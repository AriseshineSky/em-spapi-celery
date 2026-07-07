# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import time
import json

import requests

class FixerExchangeRate(object):
    def __init__(self, api_key=None, cache_days=3):
        rates_dir = os.path.expanduser(os.path.join('~', '.fixer'))
        if not os.path.isdir(rates_dir):
            os.makedirs(rates_dir)
        self.rates_path = os.path.join(rates_dir, 'rates.txt')

        self.api_key = api_key
        self.default_rates = {
            'base': 'USD',
            'rates': {
                'USD': 1,
                'CAD': 1.2874,
                'CNY': 6.6093,
                'GBP': 0.7414,
                'INR': 64.497,
                'JPY': 112.49,
                'MXN': 18.674,
                'EUR': 0.8414,
                'AUD': 1.2994,
                'SGD': 1.34811,
                'SAR': 3.751579,
                'TRY': 5.867704
            }
        }
        self.rates = self.load_cached_rates(cache_days)
        if self.rates:
            # Set default value for cached rates
            for currency, rate in self.default_rates['rates'].items():
                self.rates['rates'].setdefault(currency, rate)

    def get_exchange_rate(self, base_currency, currencies=[]):
        if self.rates:
            return self.rates['rates']

        if self.api_key is None:
            return self.default_rates['rates']

        rates = self.default_rates

        payload = {'access_key': self.api_key, 'base': base_currency}

        if not isinstance(currencies, list):
            currencies = [currencies]

        if currencies:
            payload['symbols'] = ','.join(currencies)

        url = 'https://data.fixer.io/api/latest'
        max_retry = 6
        while max_retry > 0:
            try:
                resp = requests.get(url, params=payload)
                resp.raise_for_status()

                try:
                    rates = json.loads(resp.text)
                    if 'error' in rates or 'rates' not in rates or not rates['rates']:
                        rates = self.default_rates
                except:
                    pass

                break
            except Exception:
                time.sleep(max_retry)

                max_retry -= 1

        if base_currency not in rates['rates']:
            rates['rates'][base_currency] = 1

        self.save_rates(rates)
        self.rates = rates

        return self.rates['rates']

    def load_cached_rates(self, max_days=3):
        rates = None

        if self.is_file_old_than(self.rates_path, max_days):
            return rates

        if os.path.isfile(self.rates_path):
            with open(self.rates_path) as rates_fh:
                rates = json.load(rates_fh)

        return rates

    def save_rates(self, rates):
        with open(self.rates_path, 'w') as rates_fh:
            json.dump(rates, rates_fh)

    def is_file_old_than(self, file_path, days):
        result = False
        if os.path.isfile(file_path):
            result = (time.time() - os.path.getmtime(file_path)) > 3600 * 24 * days
        else:
            result = True

        return result
