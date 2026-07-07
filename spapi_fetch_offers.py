import pdb

import em_tasks.spapi
from em_tasks.spapi import Spapi
from em_tasks.tasks.spapi_update_item_offers_task import SpapiUpdateItemOffersTask
from em_tasks.tasks.spapi_update_catalog_items_task import SpapiUpdateCatalogItemsTask

from em_celery import get_config, logger, get_offer_service, get_product_service

asins_path = './emp_asins.txt'

cfg = get_config()

spapi_cfg = cfg['spapi']
credentials = {
  'refresh_token': spapi_cfg['lwa_refresh_token'],
  'lwa_app_id': spapi_cfg['lwa_client_id'],
  'lwa_client_secret': spapi_cfg['lwa_client_secret'],
  'aws_access_key': spapi_cfg['aws_access_key'],
  'aws_secret_key': spapi_cfg['aws_secret_key']
}
spapi = Spapi(credentials)
offer_service = get_offer_service()
product_service = get_product_service()

marketplace = 'us'
batch_size = 20
asins_buf = []
with open(asins_path) as fh:
  for line in fh:
    s = line.strip()
    if not s:
      continue

    asins_buf.append(s)
    if len(asins_buf) < batch_size:
      continue

    try:
      offer_task = SpapiUpdateItemOffersTask(spapi, offer_service, marketplace, asins_buf)
      offer_task.run()
      logger.info('[OffersFetched] %s', asins_buf)

      info_task = SpapiUpdateCatalogItemsTask(spapi, product_service, marketplace, asins_buf)
      info_task.run()
      logger.info('[InfoFetched] %s', asins_buf)
      #offers = spapi.get_item_offers_batch(marketplace, asins_buf)
      asins_buf = []
    except Exception as e: 
      logger.exception(e)
      pdb.set_trace()

if asins_buf:
  offer_task = SpapiUpdateItemOffersTask(spapi, offer_service, marketplace, asins_buf)
  offer_task.run()
  logger.info('[OffersFetched] %s', asins_buf)

  info_task = SpapiUpdateCatalogItemsTask(spapi, product_service, marketplace, asins_buf)
  info_task.run()
  logger.info('[InfoFetched] %s', asins_buf)

  asins_buf = []
