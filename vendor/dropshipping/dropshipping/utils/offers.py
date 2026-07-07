# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from dropshipping.utils import ObjectDict
from datetime import datetime


common_attrs = [
    'asin', 'country', 'product_price', 'shipping_price', 'price', 'currency',
    'condition', 'subcondition', 'time'
    # 'condition', 'subcondition', 'time', 'offer_listing_count', 'has_offer'
]


class Offer(ObjectDict):
    keys = list(common_attrs)

    def __init__(self, mapping, *args, **kwargs):
        super(Offer, self).__init__(mapping, *args, **kwargs)

    def is_intact(self):
        intact = True
        for key in self.__class__.keys:
            intact = intact and key in self

        return intact

    def is_expired(self, alive_hours):
        expired = False

        if 'time' in self:
            try:
                offer_time = datetime.strptime(self['time'][:19], '%Y-%m-%dT%H:%M:%S')
                now = datetime.utcnow()
                diff_seconds = (now - offer_time).total_seconds()
                expired = diff_seconds > 3600 * alive_hours
            except:
                expired = True
        else:
            expired = True

        return expired

    def format(self):
        item = dict()
        for key in self.keys:
            if key == 'rating' or key == 'shipping_time':
                val = self.get(key, '')
                if val:
                    val = '{}-{}'.format(val.get('min', ''), val.get('max', ''))
            elif key == 'price' or key == 'shipping_price' or key == 'product_price':
                val = '%.2f' % self.get(key)
            else:
                val = str(self.get(key, ''))
            item[key] = val

        return item

    @classmethod
    def empty_offer(cls):
        offer = dict()
        for key in cls.keys:
            offer[key] = ''

        return offer


class LowestOfferListingOffer(Offer):
    keys = list(common_attrs)
    keys.extend([
        'rating', 'feedback', 'fba', 'shipping_time', 'domestic', 'offers'
    ])

    def __init__(self, mapping, *args, **kwargs):
        super(LowestOfferListingOffer, self).__init__(mapping, *args, **kwargs)


class BuyBoxOffer(Offer):
    keys = list(common_attrs)
    keys.extend([
        'belongs_to_requester', 'seller_id'
    ])

    def __init__(self, mapping, *args, **kwargs):
        super(BuyBoxOffer, self).__init__(mapping, *args, **kwargs)
