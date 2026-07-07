# -*- coding: utf-8 -*-

from datetime import datetime
import time

# from sp_api.base.exceptions import SellingApiForbiddenException
from sp_api.base.exceptions import (
  SellingApiTooLargeException,
  SellingApiStateConflictException,
  SellingApiUnsupportedFormatException,
  SellingApiException,
  SellingApiBadRequestException,
  SellingApiNotFoundException,
  SellingApiForbiddenException,
  SellingApiRequestThrottledException,
  SellingApiServerException,
  SellingApiTemporarilyUnavailableException
)
from dropshipping.spapi.exceptions import SellingApiInvalidAsinException
from dropshipping.spapi import base, CatalogItems, CatalogItemsVersion, Products
from dropshipping.utils.offer_converters import SpItemOfferConverter, SpCompetitiveOfferConverter, SpItemOfferBatchConverter

exceptions_to_retry = (SellingApiRequestThrottledException, SellingApiServerException, SellingApiTemporarilyUnavailableException, SellingApiStateConflictException)
exceptions_not_retry = (SellingApiNotFoundException, SellingApiForbiddenException, SellingApiTooLargeException, SellingApiUnsupportedFormatException)


marketplaceIdList = {
  "US": "ATVPDKIKX0DER",
  "CA": "A2EUQ1WTGCTBG2",
  "MX": "A1AM78C64UM0Y8",
  "BR": "A2Q3Y263D00KWC",
  "UK": "A1F83G8C2ARO7P",
  "DE": "A1PA6795UKMFR9",
  "ES": "A1RKKUPIHCS9HS",
  "FR": "A13V1IB3VIYZZH",
  "IT": "APJ6JRA9NG5V4",
  "BE": "AMEN7PMS3EDWL",
  "NL": "A1805IZSGTT6HS",
  "SE": "A2NODRKZP88ZB9",
  "ZA": "AE08WJ6YKNBMC",
  "PL": "A1C3SOZRARQ6R3",
  "EG": "ARBP9OOSHTCHU",
  "TR": "A33AVAJ2PDY3EV",
  "SA": "A17E79C6D8DWNP",
  "AE": "A2VIGQ35RCS4UG",
  "IN": "A21TJRUUN4KGV",
  "SG": "A19VAU5U5O7RUS",
  "AU": "A39IBJ37TRP1C6",
  "JP": "A1VC38T7YXB528"
}

marketplaceRegions = {
  "US": "NA",
  "CA": "NA",
  "MX": "NA",
  "BR": "NA",
  "UK": "EU",
  "DE": "EU",
  "ES": "EU",
  "FR": "EU",
  "IT": "EU",
  "BE": "EU",
  "NL": "EU",
  "SE": "EU",
  "ZA": "EU",
  "PL": "EU",
  "EG": "EU",
  "TR": "EU",
  "SA": "EU",
  "AE": "EU",
  "IN": "EU",
  "SG": "FE",
  "AU": "FE",
  "JP": "FE"
}

class Spapi():
  _sp_catalog_items_apis = dict()
  _sp_products_apis = dict()

  def __init__(self, credentials):
    self.credentials = credentials
    self.sp_item_offer_batch_converter = SpItemOfferBatchConverter()

  def get_catalog_items_api(self, marketplace):
    marketplace = marketplace.upper()
    if marketplace not in base.Marketplaces.__members__ or not base.Marketplaces.__members__[marketplace]:
      raise ValueError('Unkown marketplace {}'.format(marketplace))

    if marketplace not in self._sp_catalog_items_apis:
      self._sp_catalog_items_apis[marketplace] = CatalogItems(
        credentials=self.credentials, marketplace=marketplace,
        version=CatalogItemsVersion.V_2022_04_01)

    return self._sp_catalog_items_apis[marketplace]

  def get_products_api(self, marketplace):
    marketplace = marketplace.upper()
    if marketplace not in base.Marketplaces.__members__ or not base.Marketplaces.__members__[marketplace]:
      raise ValueError('Unkown marketplace {}'.format(marketplace))

    if marketplace not in self._sp_products_apis:
      self._sp_products_apis[marketplace] = Products(
        credentials=self.credentials, marketplace=marketplace)

    return self._sp_products_apis[marketplace]

  def search_catalog_items(self, asins, marketplace="US", locale='en_GB', search_type='identifiers', **kwargs):
    marketplace = marketplace.upper()
    market_id = marketplaceIdList[marketplace]
    included_data = [
      'summaries', 'attributes', 'dimensions', 'identifiers', 'images', 'productTypes',
      'relationships', 'salesRanks', 'classifications'
    ]

    possible_locale = self.get_locale(marketplace)
    if possible_locale:
      locale = possible_locale

    items = None
    max_retries = 12
    params = {'marketplaceIds': [market_id], 'includedData': ','.join(included_data), 'locale': locale}
    if search_type == 'identifiers':
      params['identifiers'] = ','.join(asins)
      params['identifiersType'] = 'ASIN'
    else:
      params['keywords'] = ','.join(asins)
      params['pageSize'] = 20
    if kwargs:
      params.update(kwargs)

    while max_retries > 0:
      try:
        items = self.get_catalog_items_api(marketplace).search_catalog_items(**params)

        break
      except SellingApiBadRequestException as e:
        msg = e.message.lower()
        if 'invalid asin' in msg:
          raise SellingApiInvalidAsinException(e.error, e.headers)

        raise e
      except exceptions_not_retry as e:
        if isinstance(e, SellingApiForbiddenException):
          time.sleep(3)

        raise e
      except exceptions_to_retry as e:
        time.sleep(max_retries)
        max_retries -= 1

        if max_retries <= 0:
          raise e

    return items

  def get_item_offers_batch(self, marketplace, asins, condition='New', add_default_offer=True):
    marketplace = marketplace.upper()
    marketplace_id = marketplaceIdList[marketplace]

    sp_products_api = self.get_products_api(marketplace)

    offers = None
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    max_retries = 12
    while max_retries > 0:
      try:
        requests = []
        for asin in asins:
          requests.append({
            'uri': '/products/pricing/v0/items/{}/offers'.format(asin),
            'method': 'GET',
            'MarketplaceId': marketplace_id,
            'ItemCondition': condition,
          })
        responses = sp_products_api.get_item_offers_batch(requests)

        offers = self.sp_item_offer_batch_converter.convert(responses)
        if offers and isinstance(offers, dict) and add_default_offer:
          for asin in asins:
            if asin in offers:
              continue

            offers[asin] = {'asin': asin, 'offers': [], 'summary': '', 'time': now}

        break
      except SellingApiBadRequestException as e:
        if 'invalid ASIN' in e.message:
          raise SellingApiInvalidAsinException(e.error, e.headers)

        raise e
      except exceptions_not_retry as e:
        if isinstance(e, SellingApiForbiddenException):
          time.sleep(7)

        raise e
      except exceptions_to_retry as e:
        time.sleep(max_retries)
        max_retries -= 1

        if max_retries <= 0:
          raise e

    return offers

  def get_locale(self, marketplace):
    marketplace = marketplace.upper()
    if marketplace in ['UK', 'DE', 'BE']:
      locale = 'en_GB'
    elif marketplace == 'FR':
      locale = 'fr_FR'
    elif marketplace == 'IT':
      locale = 'it_IT'
    elif marketplace == 'ES':
      locale = 'es_ES'
    elif marketplace in ['US', 'JP']:
      locale = 'en_US'
    elif marketplace == 'TR':
      locale = 'tr_TR'
    elif marketplace == 'AU':
      locale = 'en_AU'
    elif marketplace == 'MX':
      locale = 'es_MX'
    elif marketplace == 'NL':
      locale = 'nl_NL'
    elif marketplace == 'SE':
      locale = 'sv_SE'
    elif marketplace == 'PL':
      locale = 'pl_PL'
    elif marketplace == 'SG':
      locale = 'en_SG'
    elif marketplace == 'CA':
      locale = 'en_CA'
    elif marketplace in ['EG', 'SA', 'AE']:
      locale = 'en_AE'
    elif marketplace == 'IN':
      locale = 'en_IN'
    elif marketplace == 'IE':
      locale = 'en_IE'
    else:
      locale = None

    return locale

  @classmethod
  def get_marketplace_region(cls, marketplace):
    m = marketplace.upper()
    return marketplaceRegions.get(m, None)
