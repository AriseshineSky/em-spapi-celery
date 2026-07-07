import os
import traceback
import requests
import re
import time
import json

from dropshipping.utils.es_service import EsService


class AsinMatcher:
    def __init__(self, host=None, port=80, user=None, password=None, index_name='listing-mapping'):
        self.es_client = EsService(host, port, user, password)
        self.asin_pattern = re.compile("^B\d{2}\w{7}|\d{9}(X|\d)$")
        self.index_name = index_name

    def match_asins(self, source_asins, page_size=500):
        isbns = [self.pad_asin(isbn).lower() for isbn in source_asins]
        query = {
            "terms": {
                "isbn": isbns
            }
        }

        return self.search(query, page_size=page_size)

    def match_source_asins(self, asins, page_size=500):
        asins = [self.pad_asin(asin) for asin in asins]
        query = {'terms': {'_id': asins}}

        return self.search(query, page_size=page_size)

    def search(self, query, page_size=500):
        results = dict()
        page = 0
        while True:
            try:
                offset = page * page_size
                if offset > 10000:
                    break

                params = {
                    'index': self.index_name,
                    'from_': offset,
                    'size': page_size,
                    'body': {
                        'query': query
                    }
                }

                data = self.es_client.search(**params)

                if data['hits']['total'] == 0:
                    break

                for row in data['hits']['hits']:
                    asin = row['_source']['asin']
                    isbn = row['_source']['isbn']
                    results[asin] = isbn

                page = page + 1
                if data['hits']['total'] <= page * page_size or offset + page_size > 10000:
                    break
            except Exception:
                break

        return results

    @staticmethod
    def pad_asin(asin):
        if len(asin) < 10 and not asin.lower().startswith('b'):
            asin = "{0:0>10}".format(asin)

        return asin

    def is_valid_asin(self, asin):
        return self.asin_pattern.match(asin) is not None


class AsinMatchServerError(Exception):
    """
    AsinMatchServerError shall be raised when ConnectionError, TooManyRedirects, HTTPError(5XX) happens.
    """


class AsinInvalidError(ValueError):
    """
    AsinInvalidError shall be raised when asin does not match pattern "^B\d{2}\w{7}|\d{9}(X|\d)$".
    """
