# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime

from dropshipping.utils.es_service import EsService


class RankService(object):
    def save_sales_ranks(self, sales_ranks, country_code):
        raise NotImplementedError()

    def get_sales_ranks_for_asin(self, asins, country_code):
        raise NotImplementedError()


class EsRankService(RankService, EsService):
    def save_sales_ranks(self, sales_ranks, country_code, ignore_empty=True):
        if not self.active:
            return False

        service_ranks = []

        country_code = country_code.lower()
        common_args = {
            '_op_type': 'index',
            '_index': 'rank_{}'.format(country_code),
            '_type': '_doc'
        }
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        for asin, sales_rank_item in sales_ranks.items():
            if ignore_empty and not sales_rank_item['sales_ranks']:
                continue
            service_rank = dict()
            service_rank.update(common_args)
            service_rank['_id'] = asin
            service_rank['_source'] = {
                'asin': asin,
                'sales_ranks': json.dumps(sales_rank_item['sales_ranks']),
                'time': sales_rank_item.get('time', cur_time)
            }

            service_ranks.append(service_rank)

        return self._bulk(service_ranks)

    def get_sales_ranks_for_asin(self, asins, country_code):
        if not self.active:
            return False

        params = {
            'index': 'rank_{}'.format(country_code.lower()),
            'from_': 0,
            'size': len(asins),
            'doc_type': '_doc',
            'body': {
                'query': {'terms': {'_id': asins}}
            }
        }

        return self.search(**params)
