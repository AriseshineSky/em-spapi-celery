# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com


class EsTrackingConverter(object):
    def convert(self, data):
        result = dict()

        if not data:
            return result

        for item in data.get('hits', {}).get('hits', []):
            result[item['_id']] = {
                'order_id': item['_source']['order_id'],
                'tracking': item['_source'].get('tracking', None),
                'time': item['_source']['time']
            }

        return result


class EsTrackingStatusConverter(object):
    def convert(self, data):
        result = dict()

        if not data:
            return result

        for item in data.get('hits', {}).get('hits', []):
            result[item['_id']] = item['_source']

        return result
