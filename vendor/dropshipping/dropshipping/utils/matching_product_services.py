# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime

from dropshipping.utils.es_service import EsService


class EsMatchingProductService(EsService):
    def save_matching_products(self, matching_products, country_code):
        if not self.active:
            return False

        service_matching_products = []

        country_code = country_code.lower()
        common_args = {
            '_op_type': 'index',
            '_index': 'matching_products_{}'.format(country_code),
            '_type': '_doc'
        }
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        for asin, matching_product in matching_products.items():
            service_matching_product = dict()
            service_matching_product.update(common_args)
            service_matching_product['_id'] = asin
            service_matching_product['_source'] = {
                'asin': asin,
                'matching_product': json.dumps(matching_product),
                'time': cur_time
            }

            service_matching_products.append(service_matching_product)

        return self._bulk(service_matching_products)

    def get_matching_product_for_asin(self, asins, country_code):
        if not self.active:
            return False

        params = {
            'index': 'matching_products_{}'.format(country_code.lower()),
            'from_': 0,
            'size': len(asins),
            'doc_type': '_doc',
            'body': {
                'query': {'terms': {'_id': asins}}
            }
        }

        return self.search(**params)


class DvEsMatchingProductService(EsService):
    def get_matching_product_for_asin(self, asins, country_code):
        if not self.active:
            return False

        params = {
            'index': 'product',
            'from_': 0,
            'size': len(asins),
            'doc_type': country_code.lower(),
            'body': {
                'query': {'terms': {'_id': asins}}
            }
        }

        return self.search(**params)
