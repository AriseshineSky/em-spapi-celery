# -*- coding: utf-8 -*-

import datetime
import time
import re

import dateutil
import dateutil.parser
from sentry_sdk import capture_exception
from sp_api.base.exceptions import SellingApiForbiddenException, SellingApiBadRequestException

from dropshipping.spapi.exceptions import SellingApiInvalidAsinException

from em_tasks import logger
from em_tasks.spapi import exceptions_to_retry, exceptions_not_retry


# Per-task run stats (one doc per task run).
TASK_STATS_INDEX = "spapi_item_offers_task_stats"
# ASINs for which no offer could be retrieved (single index across marketplaces;
# marketplace is stored as a field on each document).
MISSING_OFFER_ASINS_INDEX = "spapi_item_offers_missing_asins"

_offer_product_indices_ready = False


def ensure_item_offers_product_indices(product_service):
  """Create the ProductService indices used by item-offers tasks.

  Called once per forked worker process from ``em_celery.worker``'s
  ``worker_process_init`` signal so the stats / missing-ASIN indices exist
  before tasks start writing to them.
  """
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


class SpapiUpdateItemOffersTask():
  def __init__(self, spapi, offer_service, marketplace, asins, condition='new', error_service=None):
    self.spapi = spapi
    self.error_service = error_service
    self.offer_service = offer_service
    self.marketplace = marketplace.lower()
    self.asins = asins
    self.condition = condition.lower()

  def run(self):
    offer_type = 'lowest_offer_listings'

    offers = None
    while True:
      try:
        offers = self.spapi.get_item_offers_batch(self.marketplace, self.asins, self.condition)
        break
      except SellingApiForbiddenException as e:
        raise e
      except exceptions_to_retry as e:
        time.sleep(3)
      except SellingApiInvalidAsinException as e:
        break
        # matched = re.match(r'([A-Z0-9]{10}) is an invalid ASIN', e.message)
        # if not matched:
        #   break

        # asin = matched.groups()[0]
        # if asin in self.asins:
        #   self.asins.remove(asin)

        #   if not self.asins:
        #     break
      except SellingApiBadRequestException:
        break
      except exceptions_not_retry as e:
        break

    if not offers:
      if self.error_service:
        try:
          self.error_service.save_no_offer_asins(
            "offer", self.asins, self.marketplace
          )
        except:
          pass

      return

    try:
      result = self.offer_service.save_item_offers(
        offer_type, offers, self.marketplace, self.condition)
      if result:
        logger.debug('[OfferSaved] %s', offers.keys())
      else:
        logger.debug('[OfferSaveFailed] Fetched: %s', offers)
    except Exception as e:
      logger.debug('[OfferSaveFailed] Fetched: %s', offers)

      try:
        capture_exception(e)
      except:
        pass

    return offers
