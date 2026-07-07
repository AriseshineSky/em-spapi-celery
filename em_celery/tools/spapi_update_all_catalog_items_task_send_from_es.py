# -*- coding: utf-8 -*-

import os
import datetime
import time

import click
from kombu import Connection
from dropshipping.utils.utils import is_asin_valid
import dateutil
import dateutil.parser
import redis
from urllib.parse import urlparse

from em_celery import logger, get_product_service
from em_celery.tasks.spapi_update_catalog_items_task import spapi_update_catalog_items
from em_celery.tools._sender_common import broker_option, configure_sender, normalize_broker


marketplaces = ["us", "uk", "de", "it", "jp", "ca", "mx", "ae", "in", "fr", "pl", "be", "nl"]
task_batch_size_by_marketplace = {"jp": 10}

# load_products_by_after_search(..., key="timestamp") sorts on this field; empty indices need a mapping.
ASIN_NO_INFO_INDEX_BODY = {
    "mappings": {
        "properties": {
            "asin": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "time": {"type": "date"},
        }
    }
}


@click.command('Send spapi update catalog items task to worker.')
@broker_option()
@click.option('-t', '--ttl', type=int, default=168, help='Catalog items alive hours, default is 168.')
@click.option('-f', '--force', is_flag=True, help='Force to update catalog items.')
@click.option('-q', '--qps', type=float, help='Quantity per second (QPS) to send task.')
def send_spapi_catalog_items_update_task(broker_url, qps, ttl=168, force=False):
  configure_sender('em_celery.tools.spapi_update_all_catalog_items_task_send_from_es',
                   'spapi_update_catalog_items_task_sender.log')
  broker_url = normalize_broker(broker_url)

  sender = SpapiUpdateCatalogItemsTaskSender(broker_url, qps, ttl, force)
  sender.run()


class SpapiUpdateCatalogItemsTaskSender():

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

  def __init__(self, broker_url, qps, ttl, force):
    self.product_service = get_product_service()
    self.broker_url = broker_url
    self.qps = qps
    self.ttl = ttl
    self.force = force
    self.last_send_time = None
    self.connection = Connection(self.broker_url)
    self.search_opts = {'_source': ['asin', 'time']}
    self.redis = self.get_redis_client(broker_url)
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
    time_key = "timestamp"
    default_task_batch_size = 20

    while True:
        for marketplace in marketplaces:
            indice_name = 'amz_products_api_{}_v2'.format(marketplace)
            queue = 'SpapiCatalogItemsUpdate_{}'.format(marketplace.upper())

            if not self.is_queue_need_to_send(queue):
                continue

            search_opts = {'_source': ['asin', 'time']}
            asin_indice_name = 'amz_asins_{}_no_info'.format(marketplace)
            task_batch_size = task_batch_size_by_marketplace[marketplace] if marketplace in task_batch_size_by_marketplace else default_task_batch_size

            if not self.product_service.ensure_indice(asin_indice_name, ASIN_NO_INFO_INDEX_BODY):
                logger.warning(
                    "Skipping %s: index %s is missing and could not be created "
                    "(e.g. cluster shard limit).",
                    marketplace,
                    asin_indice_name,
                )
                continue
            for s, _ in self.product_service.load_products_by_after_search(asin_indice_name, "1999-01-01T00:00:01.722593+00:00", time_key):
                if not is_asin_valid(s):
                  continue

                asins_buf.append(s)
                if len(asins_buf) < batch_size:
                  continue

                self.process_products(asins_buf, indice_name, search_opts, marketplace, queue, task_batch_size)
                asins_buf = []

                if self.is_queue_full(queue):
                    break

            if asins_buf:
                self.process_products(asins_buf, indice_name, search_opts, marketplace, queue, task_batch_size)
                asins_buf = []
                if self.is_queue_full(queue):
                    break

        time.sleep(60 * 10)

  def process_products(self, asins, indice_name, search_opts, marketplace, queue, task_batch_size):
    asins_without_info = None
    if self.force:
      asins_without_info = list(asins)
    else:
      now = datetime.datetime.now()
      product_expire_time = now - datetime.timedelta(hours=self.ttl)

      self.product_service.ensure_indice(indice_name)
      products_info = self.product_service.search_products(indice_name, asins, search_opts)
      if products_info:
        asins_without_info = dict()
        for asin in asins:
          if asin not in products_info or not products_info[asin]:
            asins_without_info[asin] = None
            continue

          product_info = products_info[asin]
          product_time_s = product_info.get('time', None)
          if not product_time_s:
            asins_without_info[asin] = None
            continue

          try:
            product_time = dateutil.parser.parse(product_time_s)

            # Product information expired
            if product_time < product_expire_time:
              asins_without_info[asin] = None
              continue
          except Exception as e:
            asins_without_info[asin] = None

        asins_without_info = list(asins_without_info.keys())
      else:
        asins_without_info = list(asins)

    chunks = [asins_without_info[x:x + task_batch_size] for x in range(0, len(asins_without_info), task_batch_size)]
    for chunk in chunks:
      spapi_update_catalog_items.apply_async(
          args=(marketplace, chunk), queue=queue, connection=self.connection
      )
      logger.debug(
        'Added spapi_update_catalog_items(%s, %s)',
        marketplace, chunk
      )


if __name__ == "__main__":
  send_spapi_catalog_items_update_task()

