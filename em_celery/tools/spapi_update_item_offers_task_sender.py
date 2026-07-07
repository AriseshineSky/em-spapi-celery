# -*- coding: utf-8 -*-

import os
import datetime
import time
import json

import click
from kombu import Connection
from dropshipping.utils.utils import is_asin_valid
import dateutil
import dateutil.parser

from em_celery import logger, get_offer_service
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers
from em_celery.tools._sender_common import broker_option, configure_sender, normalize_broker


@click.command('Send spapi update item offers task to worker.')
@broker_option()
@click.option('-m', '--marketplace', type=str, default='us', help='Amazon marketplace to fetch offers.')
@click.option('-c', '--condition', type=str, default='new')
@click.option('-t', '--ttl', type=int, default=36, help='Offer alive hours, default is 36.')
@click.option('-f', '--force', is_flag=True, help='Force to update offers.')
@click.option('-q', '--qps', type=float, help='Quantity per second (QPS) to send task.')
@click.argument('asins_path')
def send_spapi_item_offers_update_task(asins_path, broker_url, qps, marketplace='us', condition='new', ttl=36, force=False):
  configure_sender('em_celery.tools.spapi_update_item_offers_task_sender',
                   'spapi_update_item_offers_task_sender.log')
  broker_url = normalize_broker(broker_url)
  asins_path = os.path.abspath(os.path.expanduser(asins_path))
  if not os.path.isfile(asins_path):
    logger.error('Could not find asins file {}'.format(asins_path))
    return

  sender = SpapiUpdateItemOffersTaskSender(broker_url, qps, marketplace, asins_path, condition, ttl, force)
  sender.run()


class SpapiUpdateItemOffersTaskSender():
  def __init__(self, broker_url, qps, marketplace, asins_path, condition, ttl, force):
    self.offer_service = get_offer_service()
    self.broker_url = broker_url
    self.marketplace = marketplace.lower()
    self.qps = qps
    self.asins_path = asins_path
    self.condition = condition
    self.ttl = ttl
    self.force = force
    self.connection = Connection(broker_url)
    self.queue = 'SpapiItemOffersUpdate_{}'.format(marketplace.upper())
    self.offer_type = 'lowest_offer_listings'
    self.last_send_time = None

  def run(self):
    asins_buf = []
    batch_size = 500
    with open(self.asins_path, encoding='utf-8', errors='ignore') as fh:
      for line in fh:
        s = line.strip()
        if not s:
          continue

        if not is_asin_valid(s):
          continue

        asins_buf.append(s)
        if len(asins_buf) < batch_size:
          continue

        self.process_products(asins_buf)
        asins_buf = []

      if asins_buf:
        self.process_products(asins_buf)
        asins_buf = []

  def process_products(self, asins):
    if self.force:
      asins_without_offer = list(asins)
    else:
      now = datetime.datetime.utcnow()
      offer_expire_time = now - datetime.timedelta(hours=self.ttl)

      asins_without_offer = dict()
      offers = dict()
      result = self.offer_service.search_offers(
        self.offer_type, asins, self.marketplace, self.condition)
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

          if not offer.get('offers'):
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


if __name__ == "__main__":
  send_spapi_item_offers_update_task()
