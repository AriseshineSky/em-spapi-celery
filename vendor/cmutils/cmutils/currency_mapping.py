# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com


class CurrencyMapping:
    """
    Give country code and return its currency.

    Read more from here:
    https://docs.developer.amazonservices.com/en_UK/dev_guide/DG_ISO3166.html,
    https://www.amazon.com/gp/help/customer/display.html?nodeId=200497820
    """
    currency_country_code_mapping = {
        'CAD': ['CA'],
        'MXN': ['MX'],
        'USD': ['US'],
        'GBP': ['UK'],
        'EUR': ['DE', 'ES', 'FR', 'IT'],
        'INR': ['IN'],
        'JPY': ['JP'],
        'CNY': ['CN'],
        'AUD': ['AU'],
        'SGD': ['SG'],
        'SAR': ['AE'],
        'TRY': ['TR']
    }

    @classmethod
    def get_currency(cls, country_code):
        """
        Give country code and return its currency.
        If not found country code, return None.
        """
        upcase_country_code = country_code.upper()
        for currency, country_codes in cls.currency_country_code_mapping.items():
            if upcase_country_code in country_codes:
                return currency

        return None

    @classmethod
    def get_supported_countries(cls):
        """
        Return supported country codes.
        """
        countries = cls.currency_country_code_mapping.values()
        result = []
        for country_list in countries:
            result.extend(country_list)

        return result

    @classmethod
    def get_supported_currencies(cls):
        """
        Return supported currencies.
        """
        return cls.currency_country_code_mapping.keys()
