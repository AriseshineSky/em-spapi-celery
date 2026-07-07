# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import json
from datetime import datetime

from kombu.transport.virtual.base import logger

from dropshipping.utils.mws_value_extracter import (
    get_string_value,
    get_boolean_value,
    get_non_negative_integer_value,
    get_non_negative_integer_with_units_value,
    get_decimal_with_units_value,
    get_dimension_value,
    get_language_value,
    get_price_value,
    get_image_value,
    get_creator_value,
    get_sales_rank_list_value
)

from dropshipping.mws import MARKETPLACE_COUNTRY_MAPPING
from pydispatch.robust import sendRobust
from dropshipping.signals import general_error


class ProductConverter(object):

    def convert(self, data):
        raise NotImplementedError()


class MwsMatchingProductConverter(ProductConverter):

    def convert(self, data):
        result = dict()

        matching_product_result_list = data.parsed
        if not isinstance(matching_product_result_list, list):
            matching_product_result_list = [matching_product_result_list]

        d = dict()
        for matching_product in matching_product_result_list:
            asin = matching_product.get('ASIN', d).get('value', None)
            if asin is None:
                continue

            marketplace = (
                matching_product.get('Product', d)
                .get('Identifiers', d)
                .get('MarketplaceASIN', d)
                .get('MarketplaceId', d)
                .get('value', None))
            country = MARKETPLACE_COUNTRY_MAPPING.get(marketplace, None)
            if country is None:
                continue

            product = matching_product.get('Product', d)

            item_attributes = dict()
            item_attributes_d = product.get('AttributeSets', d).get('ItemAttributes', d)
            item_attributes_fields = {
                'string': [
                    'Actor', 'Artist', 'AspectRatio', 'AudienceRating', 'Author', 'BackFinding',
                    'BandMaterialType', 'Binding', 'BlurayRegion', 'Brand', 'CEROAgeRating',
                    'ChainType', 'ClaspType', 'Color', 'CPUManufacturer', 'CPUType', 'Department',
                    'Director', 'Edition', 'EpisodeSequence', 'ESRBAgeRating', 'Feature',
                    'Flavor', 'Format', 'GemType', 'Genre', 'GolfClubFlex', 'HandOrientation',
                    'HardDiskInterface', 'HardwarePlatform', 'HazardousMaterialType',
                    'IssuesPerYear', 'ItemPartNumber', 'Label', 'LegalDisclaimer', 'Manufacturer',
                    'ManufacturerPartsWarrantyDescription', 'MaterialType', 'MediaType',
                    'MetalStamp', 'MetalType', 'Model', 'OperatingSystem', 'PartNumber',
                    'PegiRating', 'Platform', 'ProductGroup', 'ProductTypeName',
                    'ProductTypeSubcategory', 'PublicationDate', 'Publisher', 'RegionCode',
                    'ReleaseDate', 'RingSize', 'ShaftMaterial', 'Scent', 'SeasonSequence',
                    'SeikodoProductCode', 'Size', 'SizePerPearl', 'Studio', 'SystemMemoryType',
                    'TheatricalReleaseDate', 'Title', 'Warranty'
                ],
                'boolean': [
                    'IsAdultProduct', 'IsAutographed', 'IsEligibleForTradeIn', 'IsMemorabilia'
                ],
                'DecimalWithUnits': [
                    'CPUSpeed', 'DisplaySize', 'GolfClubLoft', 'HardDiskSize',
                    'ManufacturerMaximumAge', 'ManufacturerMinimumAge', 'MaximumResolution',
                    'OpticalZoom', 'RunningTime', 'SystemMemorySize', 'TotalDiamondWeight',
                    'TotalGemWeight'
                ],
                'CreatorType': [
                    'Creator'
                ],
                'DimensionType': [
                    'ItemDimensions', 'PackageDimensions'
                ],
                'LanguageType': [
                    'Languages'
                ],
                'Price': [
                    'ListPrice', 'WEEETaxValue'
                ],
                'nonNegativeInteger': [
                    'NumberOfDiscs', 'NumberOfIssues', 'NumberOfItems', 'NumberOfPages',
                    'NumberOfTracks', 'PackageQuantity', 'ProcessorCount', ''
                ],
                'NonNegativeIntegerWithUnits': ['SubscriptionLength'],
                'Image': ['SmallImage']
            }
            for t, fields in item_attributes_fields.items():
                if t == 'string':
                    func = get_string_value
                elif t == 'boolean':
                    func = get_boolean_value
                elif t == 'DecimalWithUnits':
                    func = get_decimal_with_units_value
                elif t == 'CreatorType':
                    func = get_creator_value
                elif t == 'DimensionType':
                    func = get_dimension_value
                elif t == 'LanguageType':
                    func = get_language_value
                elif t == 'Price':
                    func = get_price_value
                elif t == 'nonNegativeInteger':
                    func = get_non_negative_integer_value
                elif t == 'NonNegativeIntegerWithUnits':
                    func = get_non_negative_integer_with_units_value
                elif t == 'Image':
                    func = get_image_value
                else:
                    continue

                for field in fields:
                    item_attributes[field] = func(item_attributes_d.get(field, None))

            sales_ranks = get_sales_rank_list_value(product.get('SalesRankings', d))

            result[asin] = {
                'ItemAttributes': item_attributes,
                'SalesRankings': sales_ranks
            }

        return result

class EsMatchingProductConverter(ProductConverter):

    def convert(self, data):
        result = dict()

        if data:
            for item in data.get('hits', {}).get('hits', []):
                result[item['_id']] = json.loads(item['_source']['matching_product'])
        else:
            result = data

        return result


class DvEsMatchingProductConverter(ProductConverter):

    def convert(self, data):
        result = dict()

        if data:
            for item in data.get('hits', {}).get('hits', []):
                result[item['_id']] = item['_source']
        else:
            result = data

        return result


class CatalogItemsConverter(ProductConverter):

    def convert(self, data):
        result = dict()
        if not data:
            return result

        for product_dict in data.payload.get('items', []):
            cur_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S')
            if "Error" in product_dict:
                logger.error(product_dict)
                sendRobust(signal=general_error, message=json.dumps(product_dict))
                result[asin] = {
                    'asin': asin,
                    'errors': product_dict,
                }
                continue

            asin = product_dict.get('asin')
            attributes = product_dict['attributes']
            dimensions = product_dict['dimensions']
            identifiers = product_dict['identifiers']
            images = []
            for img in product_dict['images'][0]['images']:
                images.append(img['link'])

            # images = product_dict['images'][0]['images'][0]['link']

            productTypes = product_dict['productTypes']
            relationships = product_dict['relationships']
            salesRanks = product_dict['salesRanks']
            summaries = product_dict['summaries']

            try:
                title = attributes['item_name'][0]['value']
            except:
                title = ""

            if len(title) > 255:
                title = title[:255]
            try:
                brand = attributes['brand'][0]['value']
            except:
                brand = ""

            if len(brand) > 100:
                brand = brand[:100]

            try:
                format = ""
            except:
                format = ""

            try:
                sales_ranking = int(salesRanks[0]['displayGroupRanks'][0]['rank'])
            except:
                sales_ranking = 0

            try:
                weight = dimensions[0]['package']['Weight']['value']
            except:
                weight = 0

            try:
                height = dimensions[0]['package']['height']['value']
            except:
                height = 0

            try:
                length = dimensions[0]['package']['length']['value']
            except:
                length = 0

            try:
                width = dimensions[0]['package']['width']['value']
            except:
                width = 0

            lwh = int(float(height) + float(length) + float(width))

            ranks = []

            for rank in salesRanks:
                if 'classificationRanks' in rank:
                    for classicationRank in rank.get('classificationRanks', []):
                        ranks.append({
                            'category': classicationRank.get('title'),
                            'rank': classicationRank.get('rank')
                        })
                if 'displayGroupRanks' in rank:
                    for displayGroupRank in rank.get('displayGroupRanks', []):
                        ranks.append({
                            'category': displayGroupRank.get('title'),
                            'rank': displayGroupRank.get('rank')
                        })

            result[asin] = {
                'asin': asin,
                'title': title,
                'brand': brand,
                'format': format,
                'sales_rank': sales_ranking,
                'lwh': lwh,
                'attributes': attributes,
                'sales_ranks': ranks,
                'images': images,
                'productTypes': productTypes,
                'relationships': relationships,
                'identifiers': identifiers,
                'summaries': summaries,
            }
            try:
                if 'binding' in attributes:
                    result[asin]['binding'] = attributes['binding'][0]['value']

                if 'item_weight' in attributes:
                    result[asin]['item_weight'] = attributes['item_weight'][0]['value']

                if 'item_package_weight' in attributes:
                    result[asin]['item_package_weight'] = attributes['item_package_weight'][0]['value']

                if 'pages' in attributes:
                    result[asin]['pages'] = attributes['pages'][0]['value']

                if 'item_dimensions' in attributes:
                    result[asin]['item_dimensions'] = attributes['item_dimensions'][0]

                if 'item_package_dimensions' in attributes:
                    result[asin]['item_package_dimensions'] = attributes['item_package_dimensions'][0]

                if 'subject_keyword' in attributes:
                    result[asin]['subject_keyword'] = [subject['value'] for subject in attributes['subject_keyword']]

                if 'generic_keyword' in attributes:
                    result[asin]['generic_keyword'] = [subject['value'] for subject in attributes['generic_keyword']]

                if 'item_dimensions' in attributes:
                    result[asin]['item_dimensions'] = attributes['item_dimensions'][0]

                if 'edition' in summaries:
                    result[asin]['edition'] = attributes['edition'][0]['value']

                if 'manufacturer' in summaries:
                    result[asin]['manufacturer'] = attributes['manufacturer'][0]['value']

                if 'publication_date' in summaries:
                    result[asin]['publication_date'] = attributes['publication_date'][0]['value']

                if 'list_price' in summaries:
                    result[asin]['list_price'] = {'currency': attributes['list_price'][0]['currency'],
                                                         'value': attributes['list_price'][0]['value']}
            except:
                pass
            result[asin]['time'] = cur_time
        return result


