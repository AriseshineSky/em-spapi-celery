# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com
import datetime

from dropshipping.mws import COUNTRY_MARKETPLACE_MAPPING
from dropshipping.mws.exceptions import (
    InvalidSellerID,
    InvalidAccessKeyId,
    AccessDenied,
    SignatureDoesNotMatch
)

from dropshipping import logger


class PriceFinder(object):
    def __init__(self, offer_filter):
        self.offer_filter = offer_filter

    def find_offer_for_asins(self, asins, country, condition, excludeme=True):
        raise NotImplementedError()

    def is_offer_expired(self, offer_time):
        return False


class MwsPriceFinder(PriceFinder):
    def __init__(self, offer_filter, products_api, offer_converter):
        super(MwsPriceFinder, self).__init__(offer_filter)

        self._products_api = products_api
        self._offer_converter = offer_converter

        self._buf_size = 20
        self._buf = dict()

        self.original_offers = None

    def get_offers(self, parsed_response, all=False):
        converted_offers = self._offer_converter.convert(parsed_response)

        offers = dict()
        original_offers = dict()
        for asin, converted_offer_list in converted_offers.items():
            original_offers[asin] = \
                converted_offer_list.get('offers', []) if converted_offer_list else []

            if converted_offer_list is None or converted_offer_list.get('offers', None) is None:
                offers[asin] = [] if all else None
            else:
                if all:
                    offers[asin] = self.offer_filter.filter_all(
                        converted_offer_list.get('offers'))
                else:
                    offer = self.offer_filter.filter(converted_offer_list.get('offers'))
                    if offer:
                        offer['time'] = converted_offer_list.get('time')
                        #
                    offers[asin] = offer

        return (offers, original_offers)


class MwsLowestOfferListingPriceFinder(MwsPriceFinder):
    def __init__(self, offer_filter, products_api, offer_converter):
        super(MwsLowestOfferListingPriceFinder, self).__init__(
            offer_filter, products_api, offer_converter)

    def find_offer_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_lowest_offer_listings_for_asin(
                marketplaceid, asins, condition, str(excludeme))
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        offers, self.original_offers = self.get_offers(parsed_response)
        for asin in asins:
            offers.setdefault(asin, None)
            self.original_offers.setdefault(asin, [])

        return offers

    def find_offer_listings_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_lowest_offer_listings_for_asin(
                marketplaceid, asins, condition, str(excludeme))
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        offers, self.original_offers = self.get_offers(parsed_response, True)
        for asin in asins:
            offers.setdefault(asin, [])
            self.original_offers.setdefault(asin, [])

        return offers


class MwsBuyBoxPriceFinder(MwsPriceFinder):
    def __init__(self, offer_filter, products_api, offer_converter):
        super(MwsBuyBoxPriceFinder, self).__init__(offer_filter, products_api, offer_converter)

    def find_offer_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_competitive_pricing_for_asin(
                marketplaceid, asins)
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        offers, self.original_offers = self.get_offers(parsed_response)
        for asin in asins:
            offers.setdefault(asin, None)
            self.original_offers.setdefault(asin, [])

        return offers


class OfferServicePriceFinder(PriceFinder):
    def __init__(self, offer_filter, offer_service, offer_converter):
        super(OfferServicePriceFinder, self).__init__(offer_filter)

        self._offer_service = offer_service
        self._offer_converter = offer_converter
        self._buf_size = 500
        self._buf = dict()

        self.original_offers = None

    def get_offers(self, parsed_response, all=False):
        converted_offers = self._offer_converter.convert(parsed_response)

        offers = dict()
        original_offers = dict()
        for asin, converted_offer_list in converted_offers.items():
            original_offers[asin] = \
                converted_offer_list.get('offers', []) if converted_offer_list else []
            if not converted_offer_list or not converted_offer_list.get('offers', None):
                offers[asin] = [] if all else None
            else:
                if all:
                    offers[asin] = self.offer_filter.filter_all(converted_offer_list.get('offers'))
                else:
                    offers[asin] = self.offer_filter.filter(converted_offer_list.get('offers'))

                offer_time = converted_offer_list.get('time')
                offer_expired = self.is_offer_expired(offer_time)
                if isinstance(offers[asin], list):
                    offers_for_asin = offers[asin]
                else:
                    offers_for_asin = [offers[asin]]
                for offer in offers_for_asin:
                    if not offer:
                        continue

                    offer['time'] = offer_time
                    offer['expired'] = offer_expired

        return (offers, original_offers)

    def is_offer_expired(self, offer_time):
        expire_hour = self.offer_filter.get_expire_hour()
        if expire_hour is None:
            return False
        if isinstance(offer_time, str):
            offer_time = datetime.datetime.strptime(offer_time, '%Y-%m-%dT%H:%M:%S')

        if offer_time < datetime.datetime.utcnow() - datetime.timedelta(hours=expire_hour):
            return True

        return False


class OfferServiceLowestOfferListingPriceFinder(OfferServicePriceFinder):
    def find_offer_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        parsed_response = self._offer_service.get_lowest_offer_listings_for_asin(
            country, asins, condition)

        offers, self.original_offers = self.get_offers(parsed_response)
        for asin in asins:
            offers.setdefault(asin, False)
            self.original_offers.setdefault(asin, [])

        if condition.lower() != 'new':
            asins_to_find = [asin for asin, offer in offers.items() if not offer]
            if asins_to_find:
                parsed_response = self._offer_service.get_lowest_offer_listings_for_asin(country, asins_to_find, 'new')
                offers2, original_offers2 = self.get_offers(parsed_response)
                for asin, offer in offers2.items():
                    if offer:
                        offers[asin] = offer
                for asin, original_offer in original_offers2.items():
                    if original_offer:
                        self.original_offers[asin] = original_offer

        return offers

    def find_offer_listings_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        parsed_response = self._offer_service.get_lowest_offer_listings_for_asin(
            country, asins, condition)

        offers, self.original_offers = self.get_offers(parsed_response, True)
        for asin in asins:
            offers.setdefault(asin, [])
            self.original_offers.setdefault(asin, [])

        return offers


class OfferServiceBuyBoxPriceFinder(OfferServicePriceFinder):
    def find_offer_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        parsed_response = self._offer_service.get_buybox_for_asin(
            country, asins, condition)

        converted_offers = self._offer_converter.convert(parsed_response)

        all = False
        offers = dict()
        self.original_offers = dict()
        for asin, converted_offer_list in converted_offers.items():
            self.original_offers[asin] = \
                converted_offer_list.get('offers', []) if converted_offer_list else []
            if not converted_offer_list or converted_offer_list.get('offers', None) is None:
                offers[asin] = [] if all else None
            else:
                offer_time = converted_offer_list.get('time')
                if self.is_offer_expired(offer_time):
                    offers[asin] = [] if all else None
                else:
                    if all:
                        offers[asin] = self.offer_filter.filter_all(converted_offer_list.get('offers'))
                    else:
                        offer = self.offer_filter.filter(
                            converted_offer_list.get('offers'), condition=condition)
                        if offer:
                            offer['time'] = converted_offer_list.get('time')
                            offer['expired'] = False
                        offers[asin] = offer

        for asin in asins:
            offers.setdefault(asin, False)
            self.original_offers.setdefault(asin, [])

        return offers

    def is_offer_expired(self, offer_time):
        expire_hour = self.offer_filter.get_expire_hour()
        if expire_hour is None:
            return False
        if isinstance(offer_time, str):
            offer_time = datetime.datetime.strptime(offer_time, '%Y-%m-%dT%H:%M:%S')

        if offer_time < datetime.datetime.utcnow() - datetime.timedelta(hours=expire_hour):
            return True

        return False


class SpPriceFinder(PriceFinder):
    def __init__(self, offer_filter, products_api, offer_converter):
        super(SpPriceFinder, self).__init__(offer_filter)

        self._products_api = products_api
        self._offer_converter = offer_converter

        self._buf_size = 20
        self._buf = dict()

        self.original_offers = None

    def get_offers(self, parsed_response, all=False):
        converted_offers = self._offer_converter.convert(parsed_response)

        offers = dict()
        original_offers = dict()
        for asin, converted_offer_list in converted_offers.items():
            original_offers[asin] = \
                converted_offer_list.get('offers', []) if converted_offer_list else []

            if converted_offer_list is None or converted_offer_list.get('offers', None) is None:
                offers[asin] = [] if all else None
            else:
                if all:
                    offers[asin] = self.offer_filter.filter_all(
                        converted_offer_list.get('offers'))
                else:
                    offer = self.offer_filter.filter(converted_offer_list.get('offers'))
                    if offer:
                        offer['time'] = converted_offer_list.get('time')
                        #
                    offers[asin] = offer

        return (offers, original_offers)


class SpItemOfferPriceFinder(SpPriceFinder):
    def __init__(self, offer_filter, products_api, offer_converter):
        super(SpItemOfferPriceFinder, self).__init__(
            offer_filter, products_api, offer_converter)

    def find_offer_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_lowest_offer_listings_for_asin(
                marketplaceid, asins, condition, str(excludeme))
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        offers, self.original_offers = self.get_offers(parsed_response)
        for asin in asins:
            offers.setdefault(asin, None)
            self.original_offers.setdefault(asin, [])

        return offers

    def find_offer_listings_for_asins(self, asins, country, condition, excludeme=True):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_lowest_offer_listings_for_asin(
                marketplaceid, asins, condition, str(excludeme))
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        offers, self.original_offers = self.get_offers(parsed_response, True)
        for asin in asins:
            offers.setdefault(asin, [])
            self.original_offers.setdefault(asin, [])

        return offers
