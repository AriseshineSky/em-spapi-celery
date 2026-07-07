# -*- coding: utf-8 -*-

import time
import datetime

from sp_api.base.exceptions import SellingApiForbiddenException, SellingApiBadRequestException, SellingApiException

from dropshipping.spapi.exceptions import SellingApiInvalidAsinException

from em_tasks import logger
from em_tasks.spapi.spapi_catalog_items_parser import SpapiCatalogItemsParser
from em_tasks.spapi import exceptions_to_retry, exceptions_not_retry


from em_tasks.tasks.task_stats_doc import build_catalog_stats_doc


TASK_STATS_INDEX = "spapi_item_catalog_task_stats"

_catalog_task_stats_index_ready = False


def now_ms():
  return int(time.perf_counter() * 1000)


def ensure_catalog_task_stats_index(product_service):
  """Create the unified catalog task stats index."""
  global _catalog_task_stats_index_ready
  if _catalog_task_stats_index_ready:
    return
  if product_service is None:
    return
  try:
    product_service.ensure_indice(TASK_STATS_INDEX)
  except Exception:
    logger.exception("[EnsureCatalogTaskStatsIndex] failed for %s", TASK_STATS_INDEX)
    return
  _catalog_task_stats_index_ready = True


class SpapiUpdateCatalogItemsTask():

  task_stats = {}
  minute_bucket = None
  _last_task_finish_ts = None

  def __init__(self, spapi, product_service, marketplace, asins, worker):
    self.spapi = spapi
    self.product_service = product_service
    self.worker = worker
    self.marketplace = marketplace.lower()
    self.asins = asins
    self.worker_id = worker["worker_id"]

    if self.worker_id not in SpapiUpdateCatalogItemsTask.task_stats:
      SpapiUpdateCatalogItemsTask.task_stats[self.worker_id] = {}

  def run(self):
    task_start_ms = now_ms()
    now = time.time()
    if SpapiUpdateCatalogItemsTask._last_task_finish_ts is None:
      fetch_gap_ms = 0
    else:
      fetch_gap_ms = int((now - SpapiUpdateCatalogItemsTask._last_task_finish_ts) * 1000)

    cur_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

    indice_name = 'amz_products_api_{}_v2'.format(self.marketplace)
    missing_index = f'amz_products_missing_{self.marketplace}'

    products_info = None
    spapi_start_ms = now_ms()
    while True:
      try:
        products_info = self.search_catalog_items(self.spapi, self.marketplace, self.asins)
        break
      except SellingApiForbiddenException as e:
        raise e
      except exceptions_to_retry:
        time.sleep(3)
      except exceptions_not_retry:
        break
      except (SellingApiInvalidAsinException, SellingApiBadRequestException, SellingApiException):
        break
      finally:
        SpapiUpdateCatalogItemsTask._last_task_finish_ts = time.time()

    spapi_duration_ms = now_ms() - spapi_start_ms
    total_asins = len(self.asins)

    if products_info is None:
      successful_asins = 0
      failed_asins = 0
      api_failed = 1
    else:
      successful_asins = len(products_info)
      failed_asins = total_asins - successful_asins
      api_failed = 0

    task_duration_ms = now_ms() - task_start_ms

    self._update_task_stats(
      successful_asins=successful_asins,
      failed_asins=failed_asins,
      task_duration_ms=task_duration_ms,
      spapi_duration_ms=spapi_duration_ms,
      api_failed=api_failed,
      fetch_gap_ms=fetch_gap_ms,
    )

    self.maybe_flush()

    if products_info is None:
      return

    returned_asins = set(products_info.keys())
    missing_asins = [asin for asin in self.asins if asin not in returned_asins]
    if missing_asins:
      self.save_missing_asins(missing_asins, missing_index, cur_time)

    for _, product_info in products_info.items():
      product_info['_id'] = product_info['asin']
      product_info['time'] = cur_time
    try:
      self.product_service.save_products(indice_name, list(products_info.values()))
    except Exception as e:
      logger.warning('[ProductSaveToServiceError] %s', products_info)
      logger.exception(e)
      raise e

    self.maybe_flush()

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

    worker_stats = SpapiUpdateCatalogItemsTask.task_stats.setdefault(worker_id, {})
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
    if SpapiUpdateCatalogItemsTask.minute_bucket is None:
      SpapiUpdateCatalogItemsTask.minute_bucket = now

    if now > SpapiUpdateCatalogItemsTask.minute_bucket:
      self._flush_stats_to_es(SpapiUpdateCatalogItemsTask.minute_bucket)
      SpapiUpdateCatalogItemsTask.minute_bucket = now

  def _flush_stats_to_es(self, minute_bucket):
    worker_stats = SpapiUpdateCatalogItemsTask.task_stats.get(self.worker_id, {})
    for marketplace, marketplace_stats in list(worker_stats.items()):
      stats = marketplace_stats.get(minute_bucket)
      if not stats:
        continue

      task_count = stats["task_count"]
      spapi_success_count = stats["spapi_success_count"]
      fetch_gap_count = stats["fetch_gap_count"]
      doc = build_catalog_stats_doc(
        doc_id=(
          f"catalog-{marketplace}-{self.worker_id}-pid{self.worker['pid']}_"
          f"{minute_bucket.isoformat()}"
        ),
        worker_id=self.worker_id,
        marketplace=marketplace,
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
        logger.warning("[CatalogTaskStatsSaveError] %s", doc)
        logger.exception("ES write failed")

  def save_missing_asins(self, missing_asins, index_name, cur_time):
    docs = [{'_id': asin, 'asin': asin, 'time': cur_time} for asin in missing_asins]
    try:
      self.product_service.save_products(index_name, docs)
    except Exception as e:
      logger.warning('[MissingASINSaveError] %s', missing_asins)
      logger.exception(e)

  def search_catalog_items(self, spapi, marketplace, asins):
    response = spapi.search_catalog_items(asins, marketplace=marketplace)
    if not response:
      return

    return SpapiCatalogItemsParser.parse(response)
