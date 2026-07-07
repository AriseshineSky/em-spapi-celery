# -*- coding: utf-8 -*-
"""Synchronously fetch Amazon item offers via SP-API (same task as Celery worker)."""

import os
import sys

import click
from dropshipping.utils.utils import is_asin_valid
from em_tasks.tasks.spapi_update_item_offers_task import SpapiUpdateItemOffersTask

from em_celery import logger, get_offer_service, get_spapi


def _load_asins(asins_path=None, asins=None):
  result = []
  seen = set()

  for asin in asins or []:
    asin = asin.strip().upper()
    if not is_asin_valid(asin):
      logger.warning('[InvalidASIN] %s', asin)
      continue
    if asin in seen:
      continue
    seen.add(asin)
    result.append(asin)

  if asins_path:
    asins_path = os.path.abspath(os.path.expanduser(asins_path))
    if not os.path.isfile(asins_path):
      logger.error('[ASINsFileNotFound] %s', asins_path)
      sys.exit(1)

    with open(asins_path, encoding='utf-8', errors='ignore') as fh:
      for line in fh:
        asin = line.strip().upper()
        if not asin or not is_asin_valid(asin):
          continue
        if asin in seen:
          continue
        seen.add(asin)
        result.append(asin)

  return result


def fetch_item_offers_sync_impl(marketplace, condition, asins, batch_size=20):
  spapi = get_spapi()
  offer_service = get_offer_service()
  marketplace = marketplace.lower()

  for i in range(0, len(asins), batch_size):
    chunk = asins[i:i + batch_size]
    task = SpapiUpdateItemOffersTask(spapi, offer_service, marketplace, chunk, condition)
    task.run()
    logger.info('[OffersFetched] marketplace=%s asins=%s', marketplace, chunk)


@click.command('Synchronously fetch Amazon item offers via SP-API (no Celery).')
@click.option('-m', '--marketplace', type=str, default='us', show_default=True,
              help='Amazon marketplace.')
@click.option('-c', '--condition', type=str, default='new', show_default=True,
              help='Offer condition.')
@click.option('-a', '--asin', 'asins', multiple=True,
              help='ASIN to fetch; repeat for multiple ASINs.')
@click.option('-b', '--batch-size', type=int, default=20, show_default=True,
              help='SP-API batch size (max 20).')
@click.argument('asins_path', required=False, type=click.Path(exists=True))
def fetch_item_offers_sync(marketplace, condition, asins, batch_size, asins_path):
  """Fetch offers immediately and write to offer_service (ES).

  Examples:

    spapi_fetch_item_offers_sync -m us -a B012345678 -a B098765432

    spapi_fetch_item_offers_sync -m uk urgent_asins.txt
  """
  if batch_size < 1 or batch_size > 20:
    logger.error('batch_size must be between 1 and 20')
    sys.exit(1)

  asin_list = _load_asins(asins_path, asins)
  if not asin_list:
    logger.error('No valid ASINs. Pass --asin and/or an asins file.')
    sys.exit(1)

  logger.info('[SyncFetchStart] marketplace=%s count=%d', marketplace, len(asin_list))
  fetch_item_offers_sync_impl(marketplace, condition, asin_list, batch_size)
  logger.info('[SyncFetchDone] marketplace=%s count=%d', marketplace, len(asin_list))


if __name__ == '__main__':
  fetch_item_offers_sync()
