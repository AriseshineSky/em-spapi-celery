# -*- coding: utf-8 -*-

import datetime
import time

from sp_api.base.exceptions import SellingApiForbiddenException, SellingApiBadRequestException

from dropshipping.spapi.exceptions import SellingApiInvalidAsinException

from em_tasks import logger
from em_tasks.spapi import exceptions_to_retry, exceptions_not_retry
from em_tasks.tasks.task_stats_doc import build_offer_stats_doc


TASK_STATS_INDEX = "spapi_item_offers_task_stats"
MISSING_OFFER_ASINS_INDEX = "spapi_item_offers_missing_asins"

_offer_product_indices_ready = False


def now_ms():
  return int(time.perf_counter() * 1000)


def ensure_item_offers_product_indices(product_service):
  """Create indices used by item-offers stats / missing-ASIN docs."""
  global _offer_product_indices_ready
  if _offer_product_indices_ready:
    return
  if product_service is None:
    return
  try:
    product_service.ensure_indice(TASK_STATS_INDEX)
    product_service.ensure_indice(MISSING_OFFER_ASINS_INDEX)
  except Exception:
    logger.exception(
      "[EnsureItemOffersIndices] failed for %s / %s",
      TASK_STATS_INDEX,
      MISSING_OFFER_ASINS_INDEX,
    )
    return
  _offer_product_indices_ready = True


def _count_offer_results(asins, offers):
  successful_asins = 0
  for asin in asins:
    row = offers.get(asin)
    if row and row.get("offers"):
      successful_asins += 1
  return successful_asins, max(len(asins) - successful_asins, 0)


class SpapiUpdateItemOffersTask():
  task_stats = {}
  minute_bucket = None
  _last_task_finish_ts = None

  def __init__(
    self,
    spapi,
    offer_service,
    marketplace,
    asins,
    condition='new',
    error_service=None,
    product_service=None,
    worker=None,
  ):
    self.spapi = spapi
    self.error_service = error_service
    self.offer_service = offer_service
    self.product_service = product_service
    self.worker = worker
    self.marketplace = marketplace.lower()
    self.asins = asins
    self.condition = condition.lower()
    self.worker_id = worker["worker_id"] if worker else None

    if self.worker_id and self.worker_id not in SpapiUpdateItemOffersTask.task_stats:
      SpapiUpdateItemOffersTask.task_stats[self.worker_id] = {}

  def run(self):
    offer_type = 'lowest_offer_listings'
    total_asins = len(self.asins)
    task_start_ms = now_ms()
    now = time.time()
    if SpapiUpdateItemOffersTask._last_task_finish_ts is None:
      fetch_gap_ms = 0
    else:
      fetch_gap_ms = int((now - SpapiUpdateItemOffersTask._last_task_finish_ts) * 1000)

    offers = None
    spapi_start_ms = now_ms()
    while True:
      try:
        offers = self.spapi.get_item_offers_batch(self.marketplace, self.asins, self.condition)
        break
      except SellingApiForbiddenException as e:
        raise e
      except exceptions_to_retry:
        time.sleep(3)
      except SellingApiInvalidAsinException:
        break
      except SellingApiBadRequestException:
        break
      except exceptions_not_retry:
        break
      finally:
        SpapiUpdateItemOffersTask._last_task_finish_ts = time.time()

    spapi_duration_ms = now_ms() - spapi_start_ms
    task_duration_ms = now_ms() - task_start_ms

    if offers is None:
      self._record_stats(
        successful_asins=0,
        failed_asins=0,
        task_duration_ms=task_duration_ms,
        spapi_duration_ms=spapi_duration_ms,
        api_failed=1,
        fetch_gap_ms=fetch_gap_ms,
      )
      if self.error_service:
        try:
          self.error_service.save_no_offer_asins("offer", self.asins, self.marketplace)
        except Exception:
          pass
      self.maybe_flush()
      return

    successful_asins, failed_asins = _count_offer_results(self.asins, offers)
    saved = False
    try:
      result = self.offer_service.save_item_offers(
        offer_type, offers, self.marketplace, self.condition)
      saved = bool(result)
      if saved:
        logger.debug('[OfferSaved] %s', offers.keys())
      else:
        logger.debug('[OfferSaveFailed] Fetched: %s', offers)
    except Exception as e:
      logger.debug('[OfferSaveFailed] Fetched: %s', offers)
      logger.exception(e)

    self._record_stats(
      successful_asins=successful_asins if saved else 0,
      failed_asins=failed_asins if saved else total_asins,
      task_duration_ms=task_duration_ms,
      spapi_duration_ms=spapi_duration_ms,
      api_failed=0 if saved else 1,
      fetch_gap_ms=fetch_gap_ms,
    )
    self.maybe_flush()

    return offers

  def _record_stats(
    self,
    successful_asins=0,
    failed_asins=0,
    task_duration_ms=0,
    spapi_duration_ms=0,
    api_failed=0,
    fetch_gap_ms=0,
  ):
    if not self.product_service or not self.worker_id:
      return

    self._update_task_stats(
      successful_asins=successful_asins,
      failed_asins=failed_asins,
      task_duration_ms=task_duration_ms,
      spapi_duration_ms=spapi_duration_ms,
      api_failed=api_failed,
      fetch_gap_ms=fetch_gap_ms,
    )

  def _update_task_stats(
    self,
    successful_asins=0,
    failed_asins=0,
    task_duration_ms=0,
    spapi_duration_ms=0,
    api_failed=0,
    fetch_gap_ms=0,
  ):
    now = datetime.datetime.now(datetime.timezone.utc)
    minute_key = now.replace(second=0, microsecond=0)
    worker_id = self.worker_id

    worker_stats = SpapiUpdateItemOffersTask.task_stats.setdefault(worker_id, {})
    marketplace_stats = worker_stats.setdefault(self.marketplace, {})
    stats = marketplace_stats.setdefault(
      minute_key,
      {
        "num_asins": 0,
        "successful_asins": 0,
        "failed_asins": 0,
        "task_count": 0,
        "task_duration_ms": 0,
        "spapi_duration_ms": 0,
        "api_failed": 0,
        "spapi_success_duration_ms": 0,
        "spapi_success_count": 0,
        "fetch_gap_ms": 0,
        "fetch_gap_count": 0,
      },
    )

    stats["successful_asins"] += successful_asins
    stats["failed_asins"] += failed_asins
    stats["num_asins"] += successful_asins + failed_asins
    stats["task_duration_ms"] += task_duration_ms
    stats["spapi_duration_ms"] += spapi_duration_ms
    stats["task_count"] += 1
    stats["api_failed"] += api_failed
    stats["fetch_gap_ms"] += fetch_gap_ms
    stats["fetch_gap_count"] += 1

    if api_failed == 0:
      stats["spapi_success_duration_ms"] += spapi_duration_ms
      stats["spapi_success_count"] += 1

  def maybe_flush(self):
    now = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
    if SpapiUpdateItemOffersTask.minute_bucket is None:
      SpapiUpdateItemOffersTask.minute_bucket = now

    if now > SpapiUpdateItemOffersTask.minute_bucket:
      self._flush_stats_to_es(SpapiUpdateItemOffersTask.minute_bucket)
      SpapiUpdateItemOffersTask.minute_bucket = now

  def _flush_stats_to_es(self, minute_bucket):
    if not self.product_service or not self.worker_id:
      return

    worker_stats = SpapiUpdateItemOffersTask.task_stats.get(self.worker_id, {})
    for marketplace, marketplace_stats in list(worker_stats.items()):
      stats = marketplace_stats.get(minute_bucket)
      if not stats:
        continue

      task_count = stats["task_count"]
      spapi_success_count = stats["spapi_success_count"]
      fetch_gap_count = stats["fetch_gap_count"]
      doc = build_offer_stats_doc(
        doc_id=(
          f"offers-{marketplace}-{self.worker_id}-pid{self.worker['pid']}_"
          f"{minute_bucket.isoformat()}"
        ),
        worker_id=self.worker_id,
        marketplace=marketplace,
        condition=self.condition,
        minute_bucket=minute_bucket,
        stats=stats,
        task_count=task_count,
        spapi_success_count=spapi_success_count,
        fetch_gap_count=fetch_gap_count,
      )

      try:
        self.product_service.save_products(TASK_STATS_INDEX, [doc])
        old_keys = [k for k in marketplace_stats if k <= minute_bucket]
        for k in old_keys:
          marketplace_stats.pop(k, None)
      except Exception:
        logger.warning("[OfferTaskStatsSaveError] %s", doc)
        logger.exception("ES write failed")
