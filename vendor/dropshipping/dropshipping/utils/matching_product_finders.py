# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from dropshipping.mws import COUNTRY_MARKETPLACE_MAPPING
from dropshipping.mws.exceptions import (
    InvalidSellerID,
    InvalidAccessKeyId,
    AccessDenied,
    SignatureDoesNotMatch
)
from dropshipping.utils.product_converters import (
    MwsMatchingProductConverter,
    EsMatchingProductConverter)

from dropshipping import logger


class MatchingProductFinder(object):
    def get_matching_product(self, asins, country):
        raise NotImplementedError()


class MwsMatchingProductFinder(MatchingProductFinder):
    def __init__(self, products_api):
        super(MwsMatchingProductFinder, self).__init__()

        self._products_api = products_api
        self._product_converter = MwsMatchingProductConverter()

    def get_matching_product(self, asins, country):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_matching_product(marketplaceid, asins)
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        return self._product_converter.convert(parsed_response)


class EsMatchingProductFinder(MatchingProductFinder):
    def __init__(self, matching_product_service, matching_product_converter=None):
        super(EsMatchingProductFinder, self).__init__()

        self._matching_product_service = matching_product_service
        if matching_product_converter:
            self._product_converter = matching_product_converter
        else:
            self._product_converter = EsMatchingProductConverter()

    def get_matching_product(self, asins, country):
        matching_products = self._matching_product_service.get_matching_product_for_asin(
            asins, country)

        result = self._product_converter.convert(matching_products)
        for asin in asins:
            if asin not in result:
                result[asin] = None

        return result
