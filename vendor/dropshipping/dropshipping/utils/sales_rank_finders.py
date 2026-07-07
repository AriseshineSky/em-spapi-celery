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
from dropshipping.utils.rank_parsers import MwsRankParser, EsRankParser

from dropshipping import logger


class SalesRankFinder(object):
    def find_sales_rank_for_asins(self, asins, country):
        raise NotImplementedError()


class MwsSalesRankFinder(SalesRankFinder):
    def __init__(self, products_api):
        self._products_api = products_api
        self._rank_parser = MwsRankParser()
        self.buf_size = 20

    def find_sales_rank_for_asins(self, asins, country):
        country = country.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(country)
        if not self._products_api.is_active(marketplaceid):
            return False

        try:
            parsed_response = self._products_api.get_competitive_pricing_for_asin(
                marketplaceid, asins)
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._products_api.deactivate(marketplaceid, str(e))
            parsed_response = False
        except Exception as e:
            logger.exception(e)
            parsed_response = None

        if not parsed_response:
            return parsed_response

        sales_ranks = self._rank_parser.parse(parsed_response)
        for asin in asins:
            sales_ranks.setdefault(asin, None)

        return sales_ranks


class EsSalesRankFinder(SalesRankFinder):
    def __init__(self, rank_service):
        self._rank_service = rank_service
        self._rank_parser = EsRankParser()
        self.buf_size = 500

    def find_sales_rank_for_asins(self, asins, country):
        country = country.lower()
        response = self._rank_service.get_sales_ranks_for_asin(asins, country)
        sales_ranks = self._rank_parser.parse(response)
        for asin in asins:
            sales_ranks.setdefault(asin, None)

        return sales_ranks
