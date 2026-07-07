# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
import re
from datetime import datetime

from pydispatch.robust import sendRobust

from dropshipping.mws import MARKETPLACE_COUNTRY_MAPPING
from dropshipping.signals import invalid_parameter_value
from dropshipping.utils.utils import pad_asin


class RankParser(object):

    def parse(self, data):
        raise NotImplementedError()


class MwsRankParser(RankParser):

    def parse(self, data):
        result = dict()

        if not data:
            return result

        competitive_pricings = data.parsed
        if not isinstance(competitive_pricings, list):
            competitive_pricings = [competitive_pricings]
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')

        d = dict()
        for competitive_pricing in competitive_pricings:
            asin = competitive_pricing.get('ASIN', d).get('value', None)
            if asin is None:
                continue

            error = competitive_pricing.get('Error', d)
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
                competitive_pricing.get('Product', d)
                .get('Identifiers', d)
                .get('MarketplaceASIN', d)
                .get('MarketplaceId', d)
                .get('value', None))
            country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace, None)
            if country is None:
                continue

            sales_ranks = []
            sales_rank_list = (
                competitive_pricing.get('Product', d)
                .get('SalesRankings', d)
                .get('SalesRank', []))
            if not isinstance(sales_rank_list, list):
                sales_rank_list = [sales_rank_list]
            for sales_rank in sales_rank_list:
                product_category_id = sales_rank.get('ProductCategoryId', d).get('value', None)
                rank = int(sales_rank.get('Rank', d).get('value', 0))
                sales_ranks.append({'product_category_id': product_category_id, 'rank': rank})

            result[asin] = {
                'asin': asin,
                'sales_ranks': sales_ranks,
                'time': cur_time
            }

        return result


class EsRankParser(RankParser):
    def parse(self, data):
        result = dict()

        if data:
            for item in data.get('hits', {}).get('hits', []):
                result[item['_id']] = {
                    'asin': item['_source']['asin'],
                    'sales_ranks': json.loads(item['_source']['sales_ranks']),
                    'time': item['_source']['time']
                }
        else:
            result = data

        return result


class SpCompetitiveOfferRankParser(RankParser):
    def parse(self, data):
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
                if status == 'ClientError':
                    continue
                sales_ranks = []
                sales_rank_list = item.get('Product', d).get('SalesRankings', [])
                for sales_rank in sales_rank_list:
                    product_category_id = sales_rank.get('ProductCategoryId', None)
                    rank = sales_rank.get('Rank', 0)
                    sales_ranks.append({'product_category_id': product_category_id, 'rank': rank})
                result[asin] = {
                    'asin': asin,
                    'sales_ranks': sales_ranks,
                    'time': cur_time
                }
        return result


class SpItemOfferRankParser(RankParser):
    def parse(self, data):
        result = dict()

        if not data:
            return result
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        if not isinstance(data, list):
            data = [data]
        d = dict()

        for item_offers_response in data:
            payload = item_offers_response.payload
            asin = payload.get('ASIN', None)
            if asin is None:
                continue

            sales_ranks = []
            sales_rank_list = payload.get('Summary', d).get('SalesRankings', [])
            for sales_rank in sales_rank_list:
                product_category_id = sales_rank.get('ProductCategoryId', None)
                rank = sales_rank.get('Rank', 0)
                sales_ranks.append({'product_category_id': product_category_id, 'rank': rank})
            result[asin] = {
                'asin': asin,
                'sales_ranks': sales_ranks,
                'time': cur_time
            }
        return result


class SpItemOfferBatchRankParser(RankParser):
    def parse(self, data):
        result = dict()

        if not data:
            return result
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        d = dict()

        data = data.payload.get('responses', d)

        for item_offers_response in data:
            payload = item_offers_response.get('body', d).get('payload', d)
            # asin = payload.get('ASIN', None)
            asin = item_offers_response.get('request', d).get('Asin')
            if asin is None:
                continue
            asin = pad_asin(asin)
            sales_ranks = []
            sales_rank_list = payload.get('Summary', d).get('SalesRankings', [])
            for sales_rank in sales_rank_list:
                product_category_id = sales_rank.get('ProductCategoryId', None)
                rank = sales_rank.get('Rank', 0)
                sales_ranks.append({'product_category_id': product_category_id, 'rank': rank})
            result[asin] = {
                'asin': asin,
                'sales_ranks': sales_ranks,
                'time': cur_time
            }
        return result
