# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

def get_string_value(field, default=''):
    result = None
    if field is not None:
        if isinstance(field, list):
            values = [item.get('value') for item in field]
            result = ','.join(values)
        else:
            result = field.get('value', default)

    return result

def get_boolean_value(field, default=False):
    result = None

    if field is not None:
        result = field['value'].lower() != 'false' if 'value' in field else default

    return result

def get_integer_value(field, default=0):
    result = None

    if field is not None:
        result = int(field['value']) if 'value' in field else default

    return result

def get_non_negative_integer_value(field, default=0):
    result = None

    if field is not None:
        result = int(field.get('value', default))

    return result

def get_non_negative_integer_with_units_value(field, default=0):
    result = None
    if field is not None:
        result = {
            'Units': field.get('Units', {}).get('value', ''),
            'value': int(field.get('value', default))
        }

    return result

def get_decimal_with_units_value(field, default=0):
    result = None
    if field is not None:
        result = {
            'Units': field.get('Units', {}).get('value', ''),
            'value': format_decimal_value(field.get('value', default))
        }

    return result

def get_dimension_value(field):
    result = None

    if field is not None:
        result = dict()

        d = dict()
        for k in ['Height', 'Length', 'Width', 'Weight']:
            result[k] = get_decimal_with_units_value(field.get(k, None))

    return result

def get_language_value(field):
    result = None

    if field is not None:
        d = dict()
        result = []
        languages = field.get('Language')
        if not isinstance(languages, list):
            languages = [languages]

        for language in languages:
            result.append({
                'Name': language.get('Name', d).get('value', ''),
                'Type': language.get('Type', d).get('value', '')
            })

    return result

def get_price_value(field):
    result = None

    if field is not None:
        d = dict()
        result = {
            'CurrencyCode': field.get('CurrencyCode', d).get('value', ''),
            'Amount': format_decimal_value(field.get('Amount', d).get('value', 0))
        }

    return result

def get_image_value(field):
    result = None

    d = dict()
    if field is not None:
        result = {
            'URL': field.get('URL', d).get('value', ''),
            'Height': get_decimal_with_units_value(field.get('Height', None)),
            'Width': get_decimal_with_units_value(field.get('Width', None))
        }

    return result

def get_creator_value(field):
    result = None

    if field is not None:
        if not isinstance(field, list):
            field = [field]

        result = []
        for f in field:
            result.append({
                'Role': get_string_value(f.get('Role')),
                'value': get_string_value(f)
            })

    return result

def get_sales_rank_value(field):
    result = None

    if field is not None:
        result = {
            'ProductCategoryId': get_string_value(field.get('ProductCategoryId')),
            'Rank': get_integer_value(field.get('Rank'))
        }

    return result

def get_sales_rank_list_value(field):
    result = None

    if field is not None:
        result = []
        sales_ranks = field.get('SalesRank')
        if not isinstance(sales_ranks, list):
            sales_ranks = [sales_ranks]

        for sales_rank in sales_ranks:
            result.append(get_sales_rank_value(sales_rank))

    return result

def format_decimal_value(val):
    if val is not None:
        val = round(float(val), 2)

    return val
