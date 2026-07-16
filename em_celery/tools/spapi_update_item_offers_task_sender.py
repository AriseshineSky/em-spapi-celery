# -*- coding: utf-8 -*-

import os
import datetime
import time
from collections import defaultdict

import click
import dateutil.parser

from em_celery import logger, get_offer_service
from em_celery.scheduling.send import dispatch_task
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers
from em_celery.tools._sender_common import broker_connection, broker_option, configure_sender, normalize_broker
from em_celery.tools.amazon_product_ref import load_product_refs


@click.command('Send spapi update item offers task to worker.')
@broker_option()
@click.option(
  '-m', '--marketplace',
  type=str,
  default='us',
  help='Default marketplace for bare ASINs (ignored when line is an Amazon URL).',
)
@click.option('-c', '--condition', type=str, default='new')
@click.option('-t', '--ttl', type=int, default=36, help='Offer alive hours, default is 36.')
@click.option('-f', '--force', is_flag=True, help='Force to update offers.')
@click.option('-q', '--qps', type=float, help='Quantity per second (QPS) to send task.')
@click.option(
  '-p', '--priority',
  type=int,
  default=9,
  show_default=True,
  help='Celery Redis priority (0=highest/critical … 9=bulk).',
)
@click.argument('asins_path')
def send_spapi_item_offers_update_task(
  asins_path,
  broker_url,
  qps,
  marketplace='us',
  condition='new',
  ttl=36,
  force=False,
  priority=9,
):
  """Enqueue offer updates from a file of Amazon URLs and/or bare ASINs.

  File format (one per line)::

      https://www.amazon.com/dp/B00WW3LSUO
      https://www.amazon.co.uk/dp/B0CV63L8RS
      B012345678

  URLs determine marketplace from the host; bare ASINs use ``-m``.
  """
  configure_sender('em_celery.tools.spapi_update_item_offers_task_sender',
                   'spapi_update_item_offers_task_sender.log')
  broker_url = normalize_broker(broker_url)
  asins_path = os.path.abspath(os.path.expanduser(asins_path))
  if not os.path.isfile(asins_path):
    logger.error('Could not find asins file {}'.format(asins_path))
    return

  refs = load_product_refs(asins_path, default_marketplace=marketplace)
  if not refs:
    logger.error(
      'No valid Amazon URLs/ASINs in %s (URLs need host+ASIN; bare ASINs need -m)',
      asins_path,
    )
    return

  by_marketplace = defaultdict(list)
  for mp, asin in refs:
    by_marketplace[mp].append(asin)

  for mp, asins in sorted(by_marketplace.items()):
    sender = SpapiUpdateItemOffersTaskSender(
      broker_url, qps, mp, asins, condition, ttl, force, priority,
    )
    sender.run()


class SpapiUpdateItemOffersTaskSender():
  def __init__(self, broker_url, qps, marketplace, asins, condition, ttl, force, priority=9):
    self.offer_service = get_offer_service()
    self.broker_url = broker_url
    self.marketplace = marketplace.lower()
    self.qps = qps
    self.asins = list(asins)
    self.condition = condition
    self.ttl = ttl
    self.force = force
    self.priority = priority
    self.connection = broker_connection(broker_url)
    self.queue = 'SpapiItemOffersUpdate_{}'.format(marketplace.upper())
    self.offer_type = 'lowest_offer_listings'
    self.last_send_time = None

  def run(self):
    logger.info(
      '[OfferSenderStart] marketplace=%s asins=%s priority=%s force=%s',
      self.marketplace, len(self.asins), self.priority, self.force,
    )
    batch_size = 500
    for i in range(0, len(self.asins), batch_size):
      self.process_products(self.asins[i:i + batch_size])
    logger.info(
      '[OfferSenderDone] marketplace=%s asins=%s priority=%s',
      self.marketplace, len(self.asins), self.priority,
    )

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
          except Exception:
            asins_without_offer[asin] = None

          logger.debug('[ASINHasOffer] %s', asin)

        asins_without_offer = list(asins_without_offer.keys())

    chunks = [asins_without_offer[x:x + 20] for x in range(0, len(asins_without_offer), 20)]
    for chunk in chunks:
      if self.qps and self.last_send_time:
        wait_time = 1 / self.qps - (time.time() - self.last_send_time)
        if wait_time > 0:
          logger.debug("Waiting %.3fs to send next message", wait_time)
          time.sleep(wait_time)

      self.last_send_time = time.time()

      dispatch_task(
        spapi_update_item_offers,
        args=(self.marketplace, chunk, self.condition),
        queue=self.queue,
        connection=self.connection,
        priority=self.priority,
      )
      logger.info(
        'Added spapi_update_item_offers(%s, %s, %s, priority=%s)',
        self.marketplace, chunk, self.condition, self.priority)


if __name__ == "__main__":
  send_spapi_item_offers_update_task()
