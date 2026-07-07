# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime

from dropshipping.utils.es_service import EsService


class EsProductCategoriesService(EsService):
    def save_product_categories(self, product_categories, country_code):
        if not self.active:
            return False

        service_product_categories = []

        country_code = country_code.lower()
        common_args = {
            '_op_type': 'index',
            '_index': 'products_categories_{}'.format(country_code),
            '_type': '_doc'
        }
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        for asin, product_category in product_categories.items():
            service_product_category = dict()
            service_product_category.update(common_args)
            service_product_category['_id'] = asin
            service_product_category['_source'] = {
                'asin': asin,
                'categories': json.dumps(product_category),
                'time': cur_time
            }

            service_product_categories.append(service_product_category)

        return self._bulk(service_product_categories)

    def get_product_categories_for_asin(self, asins, country_code):
        if not self.active:
            return False

        if not isinstance(asins, list):
            asins = [asins]

        params = {
            'index': 'product_categories_{}'.format(country_code.lower()),
            'from_': 0,
            'size': len(asins),
            'doc_type': '_doc',
            'body': {
                'query': {'terms': {'_id': asins}}
            }
        }

        return self.search(**params)
