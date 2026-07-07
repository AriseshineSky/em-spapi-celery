# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime


class ProductCategoriesConverter(object):

    def convert(self, data):
        raise NotImplementedError()


class MwsProductCategoriesConverter(ProductCategoriesConverter):

    def convert(self, data):
        result = dict()

        if not data:
            return result

        category_tree = data.parsed
        if 'Self' not in category_tree:
            return result

        return self.extract_categories(category_tree['Self'])

    def extract_categories(self, category_tree):
        categories = []

        categories.append({
            'id': category_tree['ProductCategoryId']['value'],
            'name': category_tree['ProductCategoryName']['value']
        })
        if 'Parent' not in category_tree:
            return categories

        parent_categories = self.extract_categories(category_tree['Parent'])
        parent_categories.extend(categories)

        return parent_categories


class EsProductCategoriesConverter(ProductCategoriesConverter):

    def convert(self, data):
        if data:
            result = dict()
            for item in data.get('hits', {}).get('hits', []):
                result[item['_id']] = {
                    'asin': item['_id'],
                    'categories': json.loads(item['_source']['categories'])
                }
        else:
            result = data

        return result
