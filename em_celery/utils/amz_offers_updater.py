# -*- coding: utf-8 -*-

import time

import redis
from dropshipping.utils.utils import is_asin_valid

from em_celery import logger
from em_celery.scheduling.priority import redis_priority_queue_depth
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers
from em_celery.tools._sender_common import broker_connection


class AmzOffersUpdater():
  def __init__(self, broker_url, qps, marketplace, condition):
    self.broker_url = broker_url
    self.marketplace = marketplace.lower()
    self.qps = qps
    self.condition = condition
    self.r = redis.Redis.from_url(broker_url)
    self.connection = broker_connection(broker_url)
    self.queue = 'SpapiItemOffersUpdate_{}'.format(marketplace.upper())
    self.offer_type = 'lowest_offer_listings'
    self.last_send_time = None

  def update_offers(self, original_asins):
    asins = []
    for asin in original_asins:
      if not is_asin_valid(asin):
        continue

      asins.append(asin)

    chunks = [asins[x:x + 20] for x in range(0, len(asins), 20)]
    for chunk in chunks:
      if self.last_send_time:
        wait_time = 1 / self.qps - (time.time() - self.last_send_time)
        if wait_time > 0:
          logger.debug("Waiting %.3fs to send next message", wait_time)
          time.sleep(wait_time)

      self.last_send_time = time.time()

      spapi_update_item_offers.apply_async(
        args=(self.marketplace, chunk, self.condition),
        queue=self.queue,
        connection=self.connection)
      logger.debug(
        'Added spapi_update_item_offers(%s, %s, %s)',
        self.marketplace, chunk, self.condition)

  def tasks_cnt(self):
    try:
      return redis_priority_queue_depth(self.r, self.queue)
    except Exception:
      return 0
