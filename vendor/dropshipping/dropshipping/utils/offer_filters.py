# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from .offers import LowestOfferListingOffer, BuyBoxOffer
from dropshipping.mws import SUBCONDITION_MAPPING


class OfferFilter(object):
    def filter(self, offers, **params):
        raise NotImplementedError()

    def filter_all(self, offers):
        raise NotImplementedError()

    def get_expire_hour(self):
        return None


class LowestOfferListingOfferFilter(OfferFilter):
    conds = [
        'rating', 'feedback', 'domestic', 'shipping_time', 'condition',
        'subcondition', 'fba', 'offers', 'price', 'expire_hour', 'picked_count', 'provider_type'
    ]

    def __init__(self, conds, strategies={}):
        super(LowestOfferListingOfferFilter, self).__init__()

        self._conds = {key: conds.get(key, None) for key in conds}
        subcondition_strategy = strategies.get('subcondition_strategy', 'ge').lower()
        if subcondition_strategy not in ['eq', 'ge']:
            self.subcondition_strategy = 'ge'
        else:
            self.subcondition_strategy = subcondition_strategy

    def filter(self, offers, **params):
        filtered_offers = self.filter_all(offers)
        filtered_offers.sort(key=calc_offer_price)
        offers_cnt = len(filtered_offers)

        min_available_offers_cnt = self._conds.get('offers', 1)
        if offers_cnt < min_available_offers_cnt:
            return None

        picked_count = min(self._conds.get('picked_count', 2), offers_cnt)
        picked_offers = filtered_offers[:picked_count]
        provider_type = self._conds.get('provider_type', 'avg')
        if provider_type == 'min':
            offer = dict(picked_offers[0])
        elif provider_type == 'max':
            offer = dict(picked_offers[-1])
        else:
            if provider_type == 'fba':
                for o in picked_offers:
                    if o['fba'] is True:
                        offer = dict(o)
                        offer['offers'] = offers_cnt
                        return offer

            offer = dict(picked_offers[0])
            offer['product_price'] = round(
                sum([o['product_price'] for o in picked_offers]) / picked_count, 2)
            offer['shipping_price'] = round(
                sum([o['shipping_price'] for o in picked_offers]) / picked_count, 2)
            offer['price'] = round(
                sum([o['price'] for o in picked_offers]) / picked_count, 2)
            offer['offers'] = offers_cnt

        return offer

    def filter_all(self, offers):
        filtered_offers = []

        for offer in offers:
            if 'fba' in self._conds and self._conds['fba'] is not None and \
                    offer['fba'] != self._conds['fba']:
                continue

            if 'price' in self._conds and self._conds['price'] is not None:
                if offer['fba'] and offer['price'] <= self._conds['price']:
                    continue

            if 'domestic' in self._conds and self._conds['domestic'] is not None:
                if 'ships_from' in offer:
                    if offer['ships_from'] == 'gb':
                        offer['ships_from'] = 'uk'
                        if offer['ships_from'] == offer['country']:
                            offer['domestic'] = True
                if 'domestic' in offer and offer['domestic'] != self._conds['domestic']:
                    continue

            if 'shipping_time' in self._conds and self._conds['shipping_time'] is not None:
                availability_type = offer.get('shipping_time', {}).get('availability_type', None)
                if availability_type and availability_type.lower().find('now') == -1:
                    continue

                if 'shipping_time' in offer and int(offer['shipping_time']['min']) > self._conds['shipping_time']:
                    continue

            if 'buybox' not in offer:
                if not offer['fba'] and 'rating' in self._conds and self._conds['rating'] is not None:
                    try:
                        offer_rating = offer['rating']['min']
                    except:
                        offer_rating = int(offer['rating'])

                    if offer_rating < self._conds['rating']:
                        continue

                if not offer['fba'] and 'feedback' in self._conds and self._conds['feedback'] is not None and \
                        int(offer['feedback']) < self._conds['feedback']:
                    continue

            if 'subcondition' in self._conds and self._conds['subcondition'] is not None:
                subcondition = offer.get('subcondition', '').lower()
                if not subcondition:
                    continue
                if subcondition in SUBCONDITION_MAPPING:
                    subcondition_val = SUBCONDITION_MAPPING[subcondition]
                    if self.subcondition_strategy == 'ge':
                        subcondition_meet = subcondition_val >= self._conds['subcondition']
                    else:
                        subcondition_meet = subcondition_val == self._conds['subcondition']

                    if not subcondition_meet:
                        continue

            filtered_offers.append(offer)

        return filtered_offers

    def get_lowest_priced_offer(self, offers):
        lowest_priced_offer = None

        if not isinstance(offers, list) or len(offers) <= 0:
            return lowest_priced_offer

        for offer in offers:
            if lowest_priced_offer is None:
                lowest_priced_offer = offer
                continue

            if lowest_priced_offer['price'] > offer['price']:
                lowest_priced_offer = offer

        return lowest_priced_offer

    def get_expire_hour(self):
        if 'expire_hour' in self._conds:
            return self._conds['expire_hour']

        return None


class BuyBoxOfferFilter(OfferFilter):
    conds = ['condition', 'expire_hour']

    def __init__(self, conds):
        super(BuyBoxOfferFilter, self).__init__()

        self._conds = {
            'condition': conds.get('condition', 'new').lower().capitalize(),
            'expire_hour': conds.get('expire_hour', 24)
        }

        # self._conds = {key: conds.get(key, '').lower().capitalize() for key in conds}

    def filter(self, offers, **params):
        filtered_offers = self.filter_all(offers)
        # condition = params.get('condition', 'Used')
        condition = self._conds['condition']

        return self.get_lowest_priced_offer_by_condition(filtered_offers, condition)

    def filter_all(self, offers):
        return offers if offers else []

    def get_lowest_priced_offer(self, offers):
        lowest_priced_offer = None

        if not isinstance(offers, list) or len(offers) <= 0:
            return lowest_priced_offer

        for offer in offers:
            if lowest_priced_offer is None:
                lowest_priced_offer = offer
                continue

            if lowest_priced_offer['price'] > offer['price']:
                lowest_priced_offer = offer

        return lowest_priced_offer

    def get_lowest_priced_offer_by_condition(self, offers, condition='Used'):
        lowest_priced_offer = None

        if not isinstance(offers, list) or len(offers) <= 0:
            return lowest_priced_offer

        condition = condition.lower()
        if condition == 'new':
            offers = [offer for offer in offers if offer['condition'].lower() == 'new']

        for offer in offers:
            if lowest_priced_offer is None:
                lowest_priced_offer = offer
                continue

            if lowest_priced_offer['price'] > offer['price']:
                lowest_priced_offer = offer

        return lowest_priced_offer

    def get_expire_hour(self):
        if 'expire_hour' in self._conds:
            return self._conds['expire_hour']

        return None


def calc_offer_price(offer):
    return offer.get('price', 0)
