# -*- coding: utf-8 -*-

import os
import datetime
import time
import redis
import click
from kombu import Connection
from dropshipping.utils.utils import is_asin_valid
import dateutil
import dateutil.parser
from urllib.parse import urlparse

from em_celery import logger, get_offer_service, get_product_service
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers
from em_celery.tools._sender_common import broker_option, configure_sender, normalize_broker


marketplaces = ["us", "uk", "de", "it", "jp", "ca", "mx", "ae", "in", "fr", "pl", "nl", "be"]

# load_products_by_after_search() defaults to key="timestamp"; empty/new indices need this mapped.
ASIN_NO_OFFER_INDEX_BODY = {
    "mappings": {
        "properties": {
            "asin": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "time": {"type": "date"},
        }
    }
}


@click.command('Send spapi update item offers task to worker.')
@broker_option()
@click.option('-c', '--condition', type=str, default='new')
@click.option('-t', '--ttl', type=int, default=36, help='Offer alive hours, default is 36.')
@click.option('-f', '--force', is_flag=True, help='Force to update offers.')
def send_spapi_item_offers_update_task(broker_url, condition='new', ttl=36, force=False):
  configure_sender('em_celery.tools.spapi_update_all_item_offers_task_send_from_es',
                   'spapi_update_item_offers_task_sender.log')
  broker_url = normalize_broker(broker_url)

  sender = SpapiUpdateItemOffersTaskSender(broker_url, condition, ttl, force)
  sender.run()


class SpapiUpdateItemOffersTaskSender():

  def get_redis_client(self, broker_url):
    url = urlparse(broker_url)
    redis_host = url.hostname
    redis_port = url.port
    redis_db = int(url.path.lstrip("/") or 0)
    redis_password = url.password

    return redis.StrictRedis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True
    )

  def __init__(self, broker_url, condition, ttl, force):
    self.offer_service = get_offer_service()
    self.broker_url = broker_url
    self.condition = condition
    self.ttl = ttl
    self.force = force
    self.connection = Connection(broker_url)
    self.offer_type = 'lowest_offer_listings'
    self.last_send_time = None
    self.redis = self.get_redis_client(broker_url)
    self.product_service = get_product_service()
    self.queue_limit = 10000
    self.queue_low_cut = 100

  def is_queue_need_to_send(self, queue):
      queue_size = self.redis.llen(queue)

      logger.debug(
          f'[current queue size] {queue}: {queue_size}'
      )
      return queue_size <= self.queue_low_cut

  def is_queue_full(self, queue):
      queue_size = self.redis.llen(queue)

      logger.debug(
          f'[current queue size] {queue}: {queue_size}'
      )
      return queue_size >= self.queue_limit

  def run(self):
    asins_buf = []
    batch_size = 2000
    while True:
        for marketplace in marketplaces:
            queue = f'SpapiItemOffersUpdate_{marketplace.upper()}'
            if not self.is_queue_need_to_send(queue):
                continue

            search_opts = {'_source': ['asin', 'time']}
            asin_indice_name = f'amz_asins_{marketplace}_no_offer'

            if not self.product_service.ensure_indice(asin_indice_name, ASIN_NO_OFFER_INDEX_BODY):
                logger.warning(
                    "Skipping %s: index %s is missing and could not be created "
                    "(e.g. cluster shard limit); free shards or add the index manually.",
                    marketplace,
                    asin_indice_name,
                )
                continue
            try:
                for s, _ in self.product_service.load_products_by_after_search(asin_indice_name):
                    if not is_asin_valid(s):
                      continue

                    asins_buf.append(s)
                    if len(asins_buf) < batch_size:
                      continue

                    self.process_products(asins_buf, marketplace, queue)
                    asins_buf = []

                    if self.is_queue_full(queue):
                        break

                if asins_buf:
                    self.process_products(asins_buf, marketplace, queue)
                    asins_buf = []
                    if self.is_queue_full(queue):
                        break
            except Exception as e:
                print(e)

        time.sleep(60 * 10)

  def process_products(self, asins, marketplace, queue):
    if self.force:
      asins_without_offer = list(asins)
    else:
      now = datetime.datetime.utcnow()
      offer_expire_time = now - datetime.timedelta(hours=self.ttl)

      asins_without_offer = dict()
      offers = dict()
      result = self.offer_service.search_offers(
        self.offer_type, asins, marketplace, self.condition)
      if not result:
        asins_without_offer = list(asins)
      else:
        while isinstance(result, dict) and 'hits' in result:
          result = result['hits']
        if isinstance(result, list):
          for offer in result:
            if not offer:
              continue

            offers[offer['_source']['asin']] = offer['_source']
        else:
          offers = result
        for asin in asins:
          if asin not in offers or not offers[asin]:
            asins_without_offer[asin] = None
            continue

          offer = offers[asin]
          offer_time_s = offer.get('time', None)
          if not offer_time_s:
            asins_without_offer[asin] = None
            continue

          try:
            offer_time = dateutil.parser.parse(offer_time_s)

            # Offer expired
            if offer_time < offer_expire_time:
              asins_without_offer[asin] = None
              continue
          except Exception as e:
            asins_without_offer[asin] = None

          logger.debug('[ASINHasOffer] %s', asin)

        asins_without_offer = list(asins_without_offer.keys())

    chunks = [asins_without_offer[x:x + 20] for x in range(0, len(asins_without_offer), 20)]
    for chunk in chunks:
      spapi_update_item_offers.apply_async(
        args=(marketplace, chunk, self.condition),
        queue=queue,
        connection=self.connection)
      logger.debug(
        'Added spapi_update_item_offers(%s, %s, %s)',
        marketplace, chunk, self.condition
      )


if __name__ == "__main__":
  send_spapi_item_offers_update_task()
