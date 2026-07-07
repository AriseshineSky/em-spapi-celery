# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime

from dropshipping.utils.es_service import EsService


class OfferService(object):
    def save_offers(self, offer_type, offers, country_code='us', condition='any'):
        raise NotImplementedError()

    def get_lowest_offer_listings_for_asin(self, country_code, asins, condition):
        raise NotImplementedError()

    def get_buybox_for_asin(self, country_code, asins, condition):
        raise NotImplementedError()


class EsOfferService(OfferService, EsService):
    def save_offers(self, offer_type, offers, country_code='us', condition='any'):
        """
        Save offer to service.
        offers : dict
            asin:list<dropshipping.utils.Offer> pairs
        country_code : string
            ALPHA-2 country code
        condition : string
            "new" or "any"
        """
        if not self.active:
            return False

        service_offers = []

        condition = condition.lower()
        if condition != 'new':
            condition = 'any'

        common_args = {
            '_op_type': 'index',
            '_index': '{}_{}_{}'.format(offer_type, country_code.lower(), condition),
            '_type': '_doc'
        }
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        for asin, offer_list in offers.items():
            service_offer = dict()
            service_offer.update(common_args)
            service_offer['_id'] = asin
            service_offer['_source'] = {
                'asin': asin,
                'offers': json.dumps(offer_list),
                'time': cur_time
            }

            service_offers.append(service_offer)

        return self._bulk(service_offers)

    def save_item_offers(self, offer_type, offers, country_code='us', condition='any'):
        """
        Save offer to service.
        offers : dict
            asin:list<dropshipping.utils.Offer> pairs
        country_code : string
            ALPHA-2 country code
        condition : string
        """
        if not self.active:
            return False

        service_offers = []

        condition = condition.lower()
        if condition != 'new':
            condition = 'any'

        common_args = {
            '_op_type': 'index',
            '_index': '{}_{}_{}'.format(offer_type, country_code.lower(), condition),
            '_type': '_doc'
        }
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        for asin, item_offer in offers.items():
            service_offer = dict()
            service_offer.update(common_args)
            service_offer['_id'] = asin
            service_offer['_source'] = {
                'asin': asin,
                'offers': json.dumps(item_offer['offers']),
                'summary': json.dumps(item_offer['summary']),
                'time': cur_time
            }
            if 'errors' in item_offer:
                service_offer['_source']['errors'] = item_offer['errors']

            service_offers.append(service_offer)

        return self._bulk(service_offers)

    def search_offers(self, offer_type, asins, country_code, condition):
        if not self.active:
            return False

        condition = condition.lower()
        if condition != 'new':
            condition = 'any'
        params = {
            'index': '{}_{}_{}'.format(offer_type, country_code.lower(), condition),
            'from_': 0,
            'size': len(asins),
            'doc_type': '_doc',
            'body': {
                'query': {'terms': {'_id': asins}}
            }
        }

        return self.search(**params)


class EsLowestOfferListingOfferService(EsOfferService):
    def __init__(self, host, port, user, password, **kwargs):
        super(EsLowestOfferListingOfferService, self).__init__(
            host, port, user, password, **kwargs)

    def get_lowest_offer_listings_for_asin(self, country_code, asins, condition):
        return self.search_offers('lowest_offer_listings', asins, country_code, condition)


class ScrapyLowestOfferListingOfferService(EsOfferService):

    def __init__(self, host, port, user, password, **kwargs):
        super(ScrapyLowestOfferListingOfferService, self).__init__(
            host, port, user, password, **kwargs)

    def get_lowest_offer_listings_for_asin(self, country_code, asins, condition):
        return self.search_offers('lowest_offer_listings', asins, country_code, condition)

    def get_buybox_for_asin(self, country_code, asins, condition):
        pass

    def search_offers(self, offer_type, asins, country_code, condition):
        if not self.active:
            return False

        condition = condition.lower()
        if condition != 'new':
            condition = 'any'

        params = {
            'index': '{}_{}_{}_scrapy'.format(offer_type, country_code.lower(), condition),
            'from_': 0,
            'size': len(asins),
            'doc_type': '_doc',
            'body': {
                'query': {'terms': {'_id': asins}}
            }
        }

        return self.search(**params)


class EsBuyBoxOfferService(EsOfferService):
    def __init__(self, host, port, user, password, **kwargs):
        super(EsBuyBoxOfferService, self).__init__(
            host, port, user, password, **kwargs)

    def save_offers(self, offer_type, offers, country_code='us', condition='any'):
        return EsOfferService.save_offers(self, offer_type, offers, country_code, 'any')

    def get_buybox_for_asin(self, country_code, asins, condition):
        return self.search_offers('buybox', asins, country_code, 'any')

