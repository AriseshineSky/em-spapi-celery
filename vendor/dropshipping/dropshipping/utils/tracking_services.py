# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime

from dropshipping.utils.es_service import EsService
from dropshipping.utils.tracking_converters import EsTrackingConverter, EsTrackingStatusConverter


class TrackingService(object):
    def save_trackings(self, trackings):
        raise NotImplementedError()

    def get_trackings(self, order_id):
        raise NotImplementedError()

    def list_trackings(self, **kwargs):
        raise NotImplementedError()

    def get_tracking_statuses(self, trackings):
        raise NotImplementedError()

    def get_untracked_orders(self):
        raise NotImplementedError()

    def get_tracked_orders(self):
        raise NotImplementedError()

    def get_orders_count(self):
        raise NotImplementedError()

    def get_untracked_orders_count(self):
        raise NotImplementedError()

    def get_tracked_orders_count(self):
        raise NotImplementedError()


class EsTrackingService(TrackingService):
    def __init__(self, host, port, user, password):
        self.es_service = EsService(host, port, user, password)
        self.converter = EsTrackingConverter()
        self.status_converter = EsTrackingStatusConverter()
        self.indice_name = 'trackings'
        self.status_indice_name = 'tracking_status'
        self.tracked_query = {'body': {'query': {'exists': {'field': 'tracking'}}}}
        self.untracked_query = {
            'body': {'query': {'bool': {'must_not': {'exists': {'field': 'tracking'}}}}}
        }

    def save_trackings(self, trackings):
        if not self.es_service.active:
            return False

        service_trackings = []

        params = {
            '_op_type': 'index',
            '_index': self.indice_name,
        }
        cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
        for order_id, tracking in trackings.items():
            service_tracking = dict()
            service_tracking.update(params)
            service_tracking['_id'] = order_id
            service_tracking['_source'] = {
                'order_id': order_id,
                'tracking': tracking if tracking else None,
                'time': cur_time
            }

            service_trackings.append(service_tracking)

        return self._bulk(service_trackings)

    def get_trackings(self, order_ids):
        '''
        Get trackings by OrderIDs

        params:
            order_ids: list or string

        return:
            False: Elasticsearch service unavailable
            None: Search request error
            dict: If order_id does not in service, tracking is None
        '''
        if not isinstance(order_ids, list):
            order_ids = [order_ids]

        if not order_ids:
            return dict()

        params = {
            'index': self.indice_name,
            'from_': 0,
            'size': len(order_ids),
            'body': {
                'query': {'terms': {'_id': order_ids}}
            }
        }

        result = self.es_service.search(**params)
        if not result:
            return result

        result = self.converter.convert(result)
        trackings = dict()
        for order_id in order_ids:
            trackings[order_id] = result.get(order_id, None)

        return trackings

    def list_trackings(self, **kwargs):
        d = dict()
        range_cond = {'range': {'time': {'format': 'dd/MM/yyyy'}}}
        query = {
            'query': {
                'bool': {
                    'must': [
                        {'exists': {'field': 'tracking'}},
                    ]
                }
            }
        }
        if 'start_date' in kwargs and kwargs['start_date']:
            range_cond['range']['time']['gte'] = kwargs['start_date']
        else:
            range_cond['range']['time']['gte'] = '01/01/1970'

        if 'end_date' in kwargs:
            range_cond['range']['time']['lte'] = kwargs['end_date']
        else:
            now = datetime.now()
            range_cond['range']['time']['lte'] = now.strftime('%d/%m/%Y')
        query['query']['bool']['must'].append(range_cond)

        params = {
            'index': self.indice_name,
            'size': 500,
            'query': query
        }
        for item in self.es_service._scan(**params):
            yield item['_source']

    def get_untracked_orders(self):
        for order_id in self.search_order_ids(self.untracked_query):
            yield order_id

    def get_tracked_orders(self):
        for order_id in self.search_order_ids(self.tracked_query):
            yield order_id

    def get_orders_count(self):
        return self.count_orders({'body': {'query': {'match_all': {}}}})

    def get_untracked_orders_count(self):
        return self.count_orders(self.untracked_query)

    def get_tracked_orders_count(self):
        return self.count_orders(self.tracked_query)

    def get_tracking_statuses(self, trackings):
        if not isinstance(trackings, list):
            trackings = [trackings]

        if not trackings:
            return dict()

        params = {
            'index': self.status_indice_name,
            'from_': 0,
            'size': len(trackings),
            'body': {
                'query': {'terms': {'_id': trackings}}
            }
        }

        result = self.es_service.search(**params)
        if not result:
            return result

        result = self.status_converter.convert(result)
        tracking_statuses = dict()
        for tracking in trackings:
            tracking_statuses[tracking] = result.get(tracking, None)

        return tracking_statuses

    def search_order_ids(self, query):
        params = {
            'index': self.indice_name,
            'size': 500,
        }
        params.update({'query': query['body']})
        for item in self.es_service._scan(**params):
            yield item['_source']['order_id']

    def count_orders(self, query):
        params = {
            'index': self.indice_name,
        }
        params.update(query)

        result = self.es_service._count(**params)
        if result:
            count = result.get('count', 0)
        else:
            count = result

        return count
