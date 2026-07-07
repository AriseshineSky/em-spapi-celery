# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from datetime import datetime
import json
import re

from pydispatch.robust import sendRobust

from dropshipping import logger
from dropshipping.mws import MARKETPLACE_COUNTRY_MAPPING
from dropshipping.signals import invalid_parameter_value
from dropshipping.spapi import Marketplaces
from dropshipping.signals import invalid_asin, general_error
from dropshipping.utils.utils import pad_asin


class OfferConverter(object):

    def convert(self, data):
        raise NotImplementedError()


class MwsLowestOfferListingOfferConverter(OfferConverter):

    def convert(self, data):
        result = dict()

        if not data:
            return result

        offer_listings_list = data.parsed
        if not isinstance(offer_listings_list, list):
            offer_listings_list = [offer_listings_list]
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')

        d = dict()
        for offer_listings in offer_listings_list:
            try:
                asin = offer_listings.get('ASIN', d).get('value', None)
            except Exception as e:
                logger.info(offer_listings)
                logger.exception(e)
                continue

            if asin is None:
                continue

            marketplace = (
                offer_listings.get('Product', d)
                .get('Identifiers', d)
                .get('MarketplaceASIN', d)
                .get('MarketplaceId', d)
                .get('value', None))
            country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace, None)
            if country is None:
                continue

            product = offer_listings.get('Product', d)
            offers = []
            lowest_offer_listing_list = product.get(
                'LowestOfferListings', d).get('LowestOfferListing', [])
            if not isinstance(lowest_offer_listing_list, list):
                lowest_offer_listing_list = [lowest_offer_listing_list]
            for offer_listing in lowest_offer_listing_list:
                qualifiers = offer_listing.get('Qualifiers', d)
                condition = qualifiers.get('ItemCondition', d).get('value')
                subcondition = qualifiers.get('ItemSubcondition', d).get('value')
                fba = qualifiers.get('FulfillmentChannel', d).get('value').lower() == 'amazon'
                domestic = qualifiers.get('ShipsDomestically', d).get('value') != 'False'

                shipping_time_str = qualifiers.get('ShippingTime', d).get('Max', d).get('value')
                shipping_time_str = shipping_time_str.split(' ').pop(0)
                if shipping_time_str.find('-') != -1:
                    shipping_time_min, shipping_time_max = \
                        [int(s) for s in shipping_time_str.split('-')]
                else:
                    shipping_time_min = int(shipping_time_str)
                    shipping_time_max = 180

                rating_str = qualifiers.get('SellerPositiveFeedbackRating', d).get('value')
                if rating_str == 'Just Launched':
                    rating = {'min': 0, 'max': 69}
                elif rating_str.find('Less than') != -1:
                    rating_str = rating_str.split('Less than ').pop()
                    max_rating = int(rating_str.replace('%', ''))
                    rating = {'min': max_rating - 10, 'max': max_rating - 1}
                else:
                    rating_min, rating_max = [int(s) for s in rating_str.strip('%').split('-')]
                    rating = {'min': rating_min, 'max': rating_max}

                feedback = int(offer_listing.get('SellerFeedbackCount', d).get('value', 0))

                landed_price = offer_listing.get('Price', d).get('LandedPrice', d)
                listing_price = offer_listing.get('Price', d).get('ListingPrice', d)
                shipping_price = offer_listing.get('Price', d).get('Shipping', d)

                currency = None
                for item in [landed_price, listing_price, shipping_price]:
                    if 'CurrencyCode' in item:
                        currency = item['CurrencyCode']['value']
                        break
                if currency is None:
                    continue

                product_price = float(listing_price.get('Amount', d).get('value', 0))
                shipping_price = float(shipping_price.get('Amount', d).get('value', 0))
                landed_price = float(landed_price.get('Amount', d).get('value', 0))
                if landed_price == 0:
                    landed_price = product_price + shipping_price

                offers.append({
                    'asin': asin,
                    'country': country,
                    'condition': condition,
                    'subcondition': subcondition,
                    'currency': currency,
                    'product_price': product_price,
                    'shipping_price': shipping_price,
                    'price': landed_price,
                    'shipping_time': {
                        'min': shipping_time_min,
                        'max': shipping_time_max
                    },
                    'rating': rating,
                    'feedback': feedback,
                    'domestic': domestic,
                    'fba': fba,
                    'type': 'MwsLowestOfferListingOffer'
                })
            result[asin] = {
                'asin': asin,
                'offers': offers,
                'time': cur_time
            }

        return result


class MwsBuyBoxOfferConverter(OfferConverter):

    def convert(self, data):
        result = dict()

        if not data:
            return result

        buybox_offers = data.parsed
        if not isinstance(buybox_offers, list):
            buybox_offers = [buybox_offers]
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')

        d = dict()
        for buybox_offer in buybox_offers:
            asin = buybox_offer.get('ASIN', d).get('value', None)
            if asin is None:
                continue

            error = buybox_offer.get('Error', d)
            if error:
                error_code = error.get('Code', d).get('value', None)
                if error_code == 'InvalidParameterValue':
                    error_msg = error.get('Message', d).get('value', '')
                    matched = re.match('ASIN (.*) is not valid for marketplace (.*)', error_msg)
                    if matched:
                        asin, marketplace = matched.groups()
                        country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace, marketplace)
                        payload = {
                            'asin': asin,
                            'marketplace': country.upper(),
                            'reason': error_msg
                        }
                        sendRobust(signal=invalid_parameter_value, sender=self, **payload)

                continue

            marketplace = (
                buybox_offer.get('Product', d)
                .get('Identifiers', d)
                .get('MarketplaceASIN', d)
                .get('MarketplaceId', d)
                .get('value', None))
            country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace, None)
            if country is None:
                continue

            offers = []
            competitive_prices = (
                buybox_offer.get('Product', d)
                .get('CompetitivePricing', d)
                .get('CompetitivePrices', d)
                .get('CompetitivePrice', []))
            if not isinstance(competitive_prices, list):
                competitive_prices = [competitive_prices]
            for competitive_price in competitive_prices:
                belongs_to_requester = competitive_price.get(
                    'belongsToRequester', d).get('value', '')
                belongs_to_requester = belongs_to_requester.lower() != 'false'
                condition = competitive_price.get('condition', d).get('value', None)
                subcondition = competitive_price.get('subcondition', d).get('value', None)
                if condition is None or subcondition is None:
                    continue

                landed_price = competitive_price.get('Price', d).get('LandedPrice', d)
                listing_price = competitive_price.get('Price', d).get('ListingPrice', d)
                shipping_price = competitive_price.get('Price', d).get('Shipping', d)

                currency = None
                for item in [landed_price, listing_price, shipping_price]:
                    if 'CurrencyCode' in item:
                        currency = item['CurrencyCode']['value']
                        break
                if currency is None:
                    continue

                product_price = float(listing_price.get('Amount', d).get('value', 0))
                shipping_price = float(shipping_price.get('Amount', d).get('value', 0))
                landed_price = float(landed_price.get('Amount', d).get('value', 0))
                if landed_price == 0:
                    landed_price = product_price + shipping_price

                offers.append({
                    'asin': asin,
                    'country': country,
                    'condition': condition,
                    'subcondition': subcondition,
                    'currency': currency,
                    'product_price': product_price,
                    'shipping_price': shipping_price,
                    'price': landed_price,
                    'belongs_to_requester': belongs_to_requester,
                    'type': 'MwsBuyBoxOffer'
                })
            result[asin] = {
                'asin': asin,
                'offers': offers,
                'time': cur_time
            }

        return result


class EsOfferConverter(OfferConverter):
    def convert(self, data):
        result = dict()

        if data:
            for item in data.get('hits', {}).get('hits', []):
                result[item['_id']] = {
                    'asin': item['_source']['asin'],
                    'offers': json.loads(item['_source']['offers']),
                    'time': item['_source']['time']
                }

        return result


class EsLowestOfferListingOfferConverter(EsOfferConverter):
    def convert(self, data):
        result = super(EsLowestOfferListingOfferConverter, self).convert(data)
        for asin, offers in result.items():
            offers['offers'] = [offer for offer in offers['offers'] if isinstance(offer, dict)]
            for offer in offers['offers']:
                try:
                    offer['type'] = 'OfferServiceLowestOfferListingOffer'
                except Exception as e:
                    pass

        return result


class EsBuyBoxOfferConverter(EsOfferConverter):
    def convert(self, data):
        result = super(EsBuyBoxOfferConverter, self).convert(data)
        for asin, offers in result.items():
            for offer in offers['offers']:
                offer['type'] = 'OfferServiceBuyBoxOffer'

        return result


class SpItemOfferConverter(OfferConverter):
    def convert(self, data):
        result = dict()

        if not data:
            return result

        if not isinstance(data, list):
            data = [data]

        d = dict()
        for item_offers_response in data:
            payload = item_offers_response.payload
            asin = payload.get('ASIN', None)
            condition = payload.get('ItemCondition', None)
            marketplace_id = payload.get('Identifier', d).get('MarketplaceId', None)
            country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace_id, None)
            if country is None or condition is None or asin is None:
                continue

            item_offers_list = payload.get('Offers', [])
            if not isinstance(item_offers_list, list):
                item_offers_list = [item_offers_list]
            cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
            offers = []
            for item_offer in item_offers_list:
                subcondition = item_offer.get('SubCondition')

                shipping_price = item_offer.get('Shipping', d).get('Amount')
                product_price = item_offer.get('ListingPrice', d).get('Amount')
                landed_price = round(shipping_price + product_price, 2)

                currency = None
                for item in [item_offer.get('Shipping', d), item_offer.get('ListingPrice', d)]:
                    if 'CurrencyCode' in item:
                        currency = item.get('CurrencyCode', None)
                if currency is None:
                    continue

                shipping_time = item_offer.get('ShippingTime', d)
                shipping_time_min = int(shipping_time.get("minimumHours", 0) / 24)
                shipping_time_max = int(shipping_time.get("maximumHours", 0) / 24)
                availability_type = shipping_time.get("availabilityType", None)

                seller_feedback_rating = item_offer.get('SellerFeedbackRating', d)
                rating = {
                    'min': seller_feedback_rating.get('SellerPositiveFeedbackRating', 0),
                    'max': seller_feedback_rating.get('SellerPositiveFeedbackRating', 0)
                }
                feedback = seller_feedback_rating.get('FeedbackCount', 0)

                ships_from = item_offer.get('ShipsFrom', d).get('Country', country).lower()
                domestic = ships_from == country.lower()

                prime_information = {
                    'is_prime': item_offer.get('PrimeInformation', d).get('IsPrime', False),
                    'is_national_prime': item_offer.get('PrimeInformation', d).get('IsNationalPrime', False)
                }

                offers.append({
                    'asin': asin,
                    'country': country,
                    'condition': condition,
                    'subcondition': subcondition,
                    'currency': currency,
                    'product_price': product_price,
                    'shipping_price': shipping_price,
                    'price': landed_price,
                    'shipping_time': {
                        'min': shipping_time_min,
                        'max': shipping_time_max,
                        'availability_type': availability_type,
                    },
                    'rating': rating,
                    'feedback': feedback,
                    'domestic': domestic,
                    'ships_from': ships_from,
                    'fba': item_offer.get('IsFulfilledByAmazon', False),
                    'is_buybox_winner': item_offer.get('IsBuyBoxWinner', False),
                    'seller_id': item_offer.get('SellerId', None),
                    'is_featured_merchant': item_offer.get('IsFeaturedMerchant', False),
                    'prime_information': prime_information,
                    'condition_notes': item_offer.get('ConditionNotes', ''),
                    'type': 'SpItemOffer'
                })
            result[asin] = {
                'asin': asin,
                'offers': offers,
                'summary': payload.get('Summary', {}),
                'time': cur_time
            }
        return result


class SpItemOfferBatchConverter(OfferConverter):
    def convert(self, data):
        result = dict()

        if not data:
            return result

        d = dict()
        for item_offers_response in data.payload.get('responses', []):
            cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
            asin = item_offers_response.get('request', d).get('Asin')
            if asin is None:
                # logger.error(item_offers_response)
                sendRobust(signal=general_error, message=json.dumps(item_offers_response))
                continue

            marketplace_id = item_offers_response.get('request', d).get('MarketplaceId', None)
            country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace_id, None)
            condition = item_offers_response.get('request', d).get('ItemCondition', None)

            if country is None or condition is None:
                result[asin] = {
                    'asin': asin,
                    'offers': [],
                    'errors': item_offers_response,
                    'summary': '',
                    'time': cur_time
                }
                # logger.error(item_offers_response)
                sendRobust(signal=general_error, message=json.dumps(item_offers_response))

            errors = item_offers_response.get('body', d).get('errors', None)
            if errors is not None:
                result[asin] = {
                    'asin': asin,
                    'offers': [],
                    'errors': errors,
                    'summary': '',
                    'time': cur_time
                }
                # logger.error(item_offers_response)
                sendRobust(signal=invalid_asin, asin=asin, country=country.upper(), errors=json.dumps(errors),
                           ignore_exc=True)
                continue

            payload = item_offers_response.get('body', d).get('payload', d)
            asin = pad_asin(asin)
            item_offers_list = payload.get('Offers', [])
            if not isinstance(item_offers_list, list):
                item_offers_list = [item_offers_list]
            offers = []
            for item_offer in item_offers_list:
                subcondition = item_offer.get('SubCondition')

                shipping_price = item_offer.get('Shipping', d).get('Amount')
                product_price = item_offer.get('ListingPrice', d).get('Amount')
                landed_price = round(shipping_price + product_price, 2)

                currency = None
                for item in [item_offer.get('Shipping', d), item_offer.get('ListingPrice', d)]:
                    if 'CurrencyCode' in item:
                        currency = item.get('CurrencyCode', None)
                if currency is None:
                    continue

                shipping_time = item_offer.get('ShippingTime', d)
                shipping_time_min = int(shipping_time.get("minimumHours", 0) / 24)
                shipping_time_max = int(shipping_time.get("maximumHours", 0) / 24)
                availability_type = shipping_time.get("availabilityType", None)

                seller_feedback_rating = item_offer.get('SellerFeedbackRating', d)
                rating = {
                    'min': seller_feedback_rating.get('SellerPositiveFeedbackRating', 0),
                    'max': seller_feedback_rating.get('SellerPositiveFeedbackRating', 0)
                }
                feedback = seller_feedback_rating.get('FeedbackCount', 0)

                ships_from = item_offer.get('ShipsFrom', d).get('Country', country).lower()
                if ships_from == 'gb':
                    ships_from = 'uk'
                domestic = ships_from == country.lower()

                prime_information = {
                    'is_prime': item_offer.get('PrimeInformation', d).get('IsPrime', False),
                    'is_national_prime': item_offer.get('PrimeInformation', d).get('IsNationalPrime', False)
                }

                offers.append({
                    'asin': asin,
                    'country': country,
                    'condition': condition,
                    'subcondition': subcondition,
                    'currency': currency,
                    'product_price': product_price,
                    'shipping_price': shipping_price,
                    'price': landed_price,
                    'shipping_time': {
                        'min': shipping_time_min,
                        'max': shipping_time_max,
                        'availability_type': availability_type,
                    },
                    'rating': rating,
                    'feedback': feedback,
                    'domestic': domestic,
                    'ships_from': ships_from,
                    'fba': item_offer.get('IsFulfilledByAmazon', False),
                    'is_buybox_winner': item_offer.get('IsBuyBoxWinner', False),
                    'seller_id': item_offer.get('SellerId', None),
                    'is_featured_merchant': item_offer.get('IsFeaturedMerchant', False),
                    'prime_information': prime_information,
                    'condition_notes': item_offer.get('ConditionNotes', ''),
                    'type': 'SpItemOffer'
                })
            result[asin] = {
                'asin': asin,
                'offers': offers,
                # 'summary': payload.get('Summary', {}),
                'summary': '',
                'time': cur_time
            }
        return result


class SpCompetitiveOfferConverter(OfferConverter):
    def convert(self, data, country=None):
        result = dict()

        if not data:
            return result
        if not isinstance(data, list):
            data = [data]
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')

        d = dict()

        for response in data:
            for item in response.payload:
                asin = item.get('ASIN', None)
                if asin is None:
                    continue

                status = item.get('status')
                if status == 'ClientError' and country is not None:
                    sendRobust(signal=invalid_asin, asin=asin, country=country.upper(), ignore_exc=True)
                    continue

                marketplace_id = item.get('Product', d).get('Identifiers', d).get('MarketplaceASIN', d).get(
                    'MarketplaceId', None)

                marketplace = Marketplaces.from_marketplace_id(marketplace_id)
                if marketplace is None:
                    continue
                country = marketplace.name.lower()

                offers = []
                competitive_prices = item.get('Product', d).get('CompetitivePricing', d).get('CompetitivePrices', [])
                for competitive_price in competitive_prices:
                    belongs_to_requester = competitive_price.get('belongsToRequester')
                    condition = competitive_price.get('condition', None)
                    subcondition = competitive_price.get('subcondition', None)
                    if condition is None or subcondition is None:
                        continue
                    landed_price = competitive_price.get('Price', d).get('LandedPrice', d)
                    listing_price = competitive_price.get('Price', d).get('ListingPrice', d)
                    shipping_price = competitive_price.get('Price', d).get('Shipping', d)

                    currency = None
                    for item1 in [landed_price, listing_price, shipping_price]:
                        if 'CurrencyCode' in item1:
                            currency = item1['CurrencyCode']
                            break
                    if currency is None:
                        continue

                    product_price = float(listing_price.get('Amount', 0))
                    shipping_price = float(shipping_price.get('Amount', 0))
                    landed_price = float(landed_price.get('Amount', 0))
                    if landed_price == 0:
                        landed_price = round(product_price + shipping_price, 2)

                    offers.append({
                        'asin': asin,
                        'country': country,
                        'condition': condition,
                        'subcondition': subcondition,
                        'currency': currency,
                        'product_price': product_price,
                        'shipping_price': shipping_price,
                        'price': landed_price,
                        'belongs_to_requester': belongs_to_requester,
                        'type': 'SpCompetitiveOffer'
                    })
                result[asin] = {
                    'asin': asin,
                    'offers': offers,
                    'time': cur_time
                }
        return result
