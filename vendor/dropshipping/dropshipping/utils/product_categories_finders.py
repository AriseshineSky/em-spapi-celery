# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from dropshipping.mws import COUNTRY_MARKETPLACE_MAPPING
from dropshipping.mws.exceptions import (
    InvalidSellerID,
    InvalidAccessKeyId,
    AccessDenied,
    SignatureDoesNotMatch
)
from dropshipping.utils.product_categories_converters import (
    MwsProductCategoriesConverter,
    EsProductCategoriesConverter)

from dropshipping import logger


class ProductCategoriesFinder(object):
    def get_product_categories(self, asins, country):
        raise NotImplementedError()


class MwsProductCategoriesFinder(ProductCategoriesFinder):
    def __init__(self, products_api):
        super(MwsProductCategoriesFinder, self).__init__()

        self._products_api = products_api
        self._product_converter = MwsProductCategoriesConverter()

    def get_product_categories(self, asin, country):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_product_categories_for_asin(
                marketplaceid, asin)
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        return {
            'asin': asin,
            'categories': self._product_converter.convert(parsed_response)
        }


class EsProductCategoriesFinder(ProductCategoriesFinder):
    def __init__(self, product_categories_service):
        super(EsProductCategoriesFinder, self).__init__()

        self._product_categories_service = product_categories_service
        self._product_converter = EsProductCategoriesConverter()

    def get_product_categories(self, asin, country):
        product_categories = self._product_categories_service.get_product_categories_for_asin(
            asin, country)

        result = self._product_converter.convert(product_categories)
        return result.get(asin, None)
