# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from mws import mws

from mws.mws import (
    Feeds,
    Reports,
    Orders,
    Products,
    Sellers,
    Finances,
    InboundShipments,
    Inventory,
    OutboundShipments,
    Recommendations,
    MARKETPLACES
)


MWS_ERROR_CODES = {
    'InputStreamDisconnected': {
        'http_status': 400,
        'mws_desc': 'There was an error reading the input stream.'
    },
    'InvalidParameterValue': {
        'http_status': 400,
        'mws_desc': 'An invalid parameter value was used, or the request size exceeded the maximum accepted size, or the request expired.'
    },
    'AccessDenied': {
        'http_status': 401,
        'mws_desc': 'Access was denied.'
    },
    'InvalidAccessKeyId': {
        'http_status': 403,
        'mws_desc': 'An invalid AWSAccessKeyId value was used.'
    },
    'SignatureDoesNotMatch': {
        'http_status': 403,
        'mws_desc': "The signature used does not match the server's calculated signature value."
    },
    'InvalidAddress': {
        'http_status': 404,
        'mws_desc': 'An invalid API section or operation value was used, or an invalid path was used.'
    },
    'InternalError': {
        'http_status': 500,
        'mws_desc': 'There was an internal service failure.'
    },
    'QuotaExceeded': {
        'http_status': 503,
        'mws_desc': 'The total number of requests in an hour was exceeded.'
    },
    'RequestThrottled': {
        'http_status': 503,
        'mws_desc': 'The frequency of requests was greater than allowed.'
    },
    'InvalidRequest': {
        'http_status': 400,
        'mws_desc': 'Request has missing or invalid parameters and cannot be parsed.'
    }
}


MARKETPLACE_COUNTRY_MAPPING = {
    'A2EUQ1WTGCTBG2': 'ca',
    'A1AM78C64UM0Y8': 'mx',
    'ATVPDKIKX0DER': 'us',
    'A2Q3Y263D00KWC': 'br',
    'A1PA6795UKMFR9': 'de',
    'A1RKKUPIHCS9HS': 'es',
    'A13V1IB3VIYZZH': 'fr',
    'APJ6JRA9NG5V4': 'it',
    'A1F83G8C2ARO7P': 'uk',
    'A21TJRUUN4KGV': 'in',
    'A1VC38T7YXB528': 'jp',
    'AAHKV2X7AFYLW': 'cn',
    'A39IBJ37TRP1C6': 'au',
    'A2VIGQ35RCS4UG': 'ae',
    'A33AVAJ2PDY3EV': 'tr',
    'A19VAU5U5O7RUS': 'sg',
    'A1805IZSGTT6HS': 'nl',
    'A17E79C6D8DWNP': 'sa'
}

COUNTRY_MARKETPLACE_MAPPING = {
    'ca': 'A2EUQ1WTGCTBG2',
    'mx': 'A1AM78C64UM0Y8',
    'us': 'ATVPDKIKX0DER',
    'br': 'A2Q3Y263D00KWC',
    'de': 'A1PA6795UKMFR9',
    'es': 'A1RKKUPIHCS9HS',
    'fr': 'A13V1IB3VIYZZH',
    'it': 'APJ6JRA9NG5V4',
    'uk': 'A1F83G8C2ARO7P',
    'in': 'A21TJRUUN4KGV',
    'jp': 'A1VC38T7YXB528',
    'cn': 'AAHKV2X7AFYLW',
    'au': 'A39IBJ37TRP1C6',
    'ae': 'A2VIGQ35RCS4UG',
    'tr': 'A33AVAJ2PDY3EV',
    'sg': 'A19VAU5U5O7RUS',
    'nl': 'A1805IZSGTT6HS',
    'sa': 'A17E79C6D8DWNP'
}

SUBCONDITION_MAPPING = {
    'new': 100,
    'mint': 90,
    'like_new': 90,
    'likenew': 90,
    'very_good': 81,
    'verygood': 80,
    'good': 70,
    'acceptable': 60,
    'poor': 50,
    'club': 40,
    'oem': 30,
    'warranty': 25,
    'refurbishedwarranty': 20,
    'refurbished_warranty': 21,
    'refurbished': 15,
    'open_box': 10,
    'openbox': 11,
    'other': 0
}

from dropshipping.mws import monkey_patches
from dropshipping.mws.decorators import mws_wrapper

Reports.update_report_acknowledgements = monkey_patches.update_report_acknowledgements

mws.MARKETPLACES.update({
    "AE": "https://mws.amazonservices.ae", # A2VIGQ35RCS4UG
    "TR": "https://mws-eu.amazonservices.com", # A33AVAJ2PDY3EV
    "SG": "https://mws-fe.amazonservices.com", # A19VAU5U5O7RUS
    "NL": "https://mws-eu.amazonservices.com", # A1805IZSGTT6HS
    "SA": "https://mws-eu.amazonservices.com", # A17E79C6D8DWNP
})


Feeds = mws_wrapper(Feeds)
Reports = mws_wrapper(Reports)
Orders = mws_wrapper(Orders)
Products = mws_wrapper(Products)
Sellers = mws_wrapper(Sellers)
Finances = mws_wrapper(Finances)
InboundShipments = mws_wrapper(InboundShipments)
Inventory = mws_wrapper(Inventory)
OutboundShipments = mws_wrapper(OutboundShipments)
Recommendations = mws_wrapper(Recommendations)
