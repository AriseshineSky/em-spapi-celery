import traceback
from elasticsearch import Elasticsearch, helpers
import requests

from dropshipping import logger
from dropshipping.utils.es_service import EsService


class ElasticProduct:
    elastic_actions = []
    es_client = None
    bulk_length = 20

    def __init__(self, host, port=9200, user=None, password=None, bulk_length=20, index_name='product'):
        self.es_client = EsService(host, port, user, password)
        self.elastic_actions = []
        self.bulk_length = bulk_length
        self.host = host
        self.index_name = index_name

    def get_by_asin(self, asin, region="US"):
        data = self.get_data([asin], region)
        for row in data['hits']['hits']:
            if 'title' in row['_source']:
                return row['_source']
        return None

    def get_data(self, asins, region="US", offset=0):
        region = region.lower()
        query = {'terms': {'_id': asins}}
        params = {
            'index': self.index_name,
            'from_': offset,
            'size': len(asins),
            "doc_type": region,
            'body': {
                'query': query
            }
        }

        return self.es_client.search(**params)

    def get_data_by_asins(self, asins, region="US", offset=0):
        map = {}

        data = self.get_data(asins, region, offset)

        if data is None or data['hits']['total'] == 0:
            return map

        for row in data['hits']['hits']:
            asin = row['_source']['asin']
            if 'title' in row['_source']:
                title = row['_source']['title']
                brand = row['_source']['brand'] if 'brand' in row['_source'] else None
                if brand is None or brand == '':
                    try:
                        brand = row['_source']['attributes']['Publisher']['value']
                    except:
                        pass

                binding = row['_source']['binding'] if 'binding' in row['_source'] else None
                group = row['_source']['ProductGroup'] if 'ProductGroup' in row['_source'] else None
                sales_rank = row['_source']['sales_rank'] if 'sales_rank' in row['_source'] else 0
                map[asin] = {'brand': brand, 'title': title, 'binding': binding, 'group': group,
                             'sales_rank': sales_rank}

        return map

    def get_by_asins(self, asins, region="US", offset=0):
        results = {}

        data = self.get_data(asins, region, offset)
        if data['hits']['total'] == 0:
            return results

        for row in data['hits']['hits']:
            if 'asin' in row['_source']:
                asin = row['_source']['asin']
            # else:
            #     print(f'Could not find asin filed: {row["_id"]}')
            #     asin = row['_id']
            #     row['_source']['asin'] = asin
                results[asin] = row['_source']

        return results

    def get_dimensions(self, asins, region="US", offset=0):
        map = {}

        data = self.get_data(asins, region, offset)
        if data['hits']['total'] == 0:
            return map

        for row in data['hits']['hits']:
            asin = row['_source']['asin']

            try:
                weight = row['_source']['attributes']['PackageDimensions']['Weight']['value']
            except:
                weight = 0

            try:
                height = row['_source']['attributes']['PackageDimensions']['Height']['value']
            except:
                height = 0

            try:
                length = row['_source']['attributes']['PackageDimensions']['Length']['value']
            except:
                length = 0

            try:
                width = row['_source']['attributes']['PackageDimensions']['Width']['value']
            except:
                width = 0

            map[asin] = {'width': width, 'length': length, 'height': height, 'weight': weight}

        return map

    def get_data_by_brand(self, brand, page=0, size=100):
        # if brand.lower() == "unknown":
        #     return []

        brand = brand.lower()
        # query = {
        #     "term": {"brand": brand}
        # }

        # query = {
        #     "match": {
        #         "brand": {"query": brand,
        #                   "operator": "and"
        #                   }
        #     }
        # }
        query = {
            "bool": {
                "should": [
                    {
                        "match": {
                            "attributes.Publisher.value": {"query": brand, "operator": "and"}
                        }
                    },
                    {
                        "match": {
                            "attributes.Manufacturer.value": {"query": brand, "operator": "and"}
                        }
                    },
                    {
                        "match": {
                            "brand": {"query": brand, "operator": "and"}
                        }
                    }
                ]
            }
        }
        ps = []

        while True:
            try:
                offset = page * size
                if offset > 10000:
                    break

                params = {
                    'index': self.index_name,
                    'from_': offset,
                    'size': size,
                    'body': {
                        'query': query
                    },
                    'request_timeout': 30
                }

                # print params
                data = self.es_client.search(**params)
                # print data

                if data['hits']['total'] == 0:
                    break

                for row in data['hits']['hits']:
                    asin = row['_source']['asin']
                    if 'title' in row['_source']:
                        try:
                            bbrand = row['_source']['brand']
                        except:
                            bbrand = ''
                        try:
                            publisher = row['_source']['attributes']['Publisher']['value']
                        except:
                            publisher = ''
                        try:
                            manufacturer = row['_source']['attributes']['Manufacturer']['value']
                        except:
                            manufacturer = ''

                        if brand.lower() in [bbrand.lower(), publisher.lower(), manufacturer.lower()]:
                            title = row['_source']['title']
                            ps.append({'brand': bbrand, 'asin': asin, 'title': title, 'publisher': publisher,
                                       'manufacturer': manufacturer})

                page = page + 1
                if data['hits']['total'] <= page * size or offset + size > 10000:
                    break
            except Exception as e:
                logger.exception(e)
                break

        return ps

    def get_data_by_brand_scroll(self, brand, page=0, size=200):

        brand = brand.lower()

        query = {
            "bool": {
                "should": [
                    {
                        "match": {
                            "attributes.Publisher.value": {"query": brand, "operator": "and"}
                        }
                    },
                    {
                        "match": {
                            "attributes.Manufacturer.value": {"query": brand, "operator": "and"}
                        }
                    },
                    {
                        "match": {
                            "brand": {"query": brand, "operator": "and"}
                        }
                    }
                ]
            }
        }
        max = '200m'
        ps = []
        params = {
            'index': self.index_name,
            'scroll': max,
            'size': size,
            'body': {
                'query': query
            },
            'request_timeout': 30
        }

        data = self.es_client.search(**params)
        sid = data['_scroll_id']
        scroll_size = data['hits']['total']
        total_size = scroll_size
        total_pages = int(total_size / size)
        page_no = 0
        total = 0
        # Start scrolling
        while scroll_size > 0:
            try:
                logger.info("Scrolling...")
                data = self.es_client.esclient.scroll(scroll_id=sid, scroll=max)
                # Update the scroll ID
                sid = data['_scroll_id']
                # Get the number of results that we returned in the last scroll
                scroll_size = len(data['hits']['hits'])
                # print "scroll size: " + str(scroll_size)
                # print data

                if data['hits']['total'] == 0:
                    break

                for row in data['hits']['hits']:
                    asin = row['_source']['asin']
                    if 'title' in row['_source']:
                        try:
                            brand = row['_source']['brand']
                        except:
                            brand = ''
                        try:
                            publisher = row['_source']['attributes']['Publisher']['value']
                        except:
                            publisher = ''
                        try:
                            manufacturer = row['_source']['attributes']['Publisher']['value']
                        except:
                            manufacturer = ''

                        if brand.lower() in [brand.lower(), publisher.lower(), manufacturer.lower()]:
                            title = row['_source']['title']
                            ps.append(
                                {'brand': row['_source']['brand'], 'asin': asin, 'title': title, 'publisher': publisher,
                                 'manufacturer': manufacturer})
                            total = total + 1
                page_no = page_no + 1

                logger.info('page %s/%s, total %s/%s' % (page_no, total_pages, total, total_size))
            except Exception as e:
                logger.exception(e)
                break

        return ps

    def search_scroll(self, query, size=200, sort=None):
        max = '999m'
        params = {
            'index': self.index_name,
            'scroll': max,
            'size': size,
            'body': {
                'query': query
            },
            'request_timeout': 30
        }

        if sort is not None:
            params['body']['sort'] = sort

        data = self.es_client.search(**params)
        sid = data['_scroll_id']
        scroll_size = data['hits']['total']
        total_size = scroll_size
        total_pages = int(total_size / size)
        page_no = 0
        total = 0
        logger.info("total % found, %s pages", total_size, total_pages)
        # Start scrolling
        while scroll_size > 0:
            try:
                logger.info("Scrolling...")
                data = self.es_client.esclient.scroll(scroll_id=sid, scroll=max)
                sid = data['_scroll_id']
                scroll_size = len(data['hits']['hits'])

                if data['hits']['total'] == 0:
                    break

                for row in data['hits']['hits']:
                    asin = row['_source']['asin']
                    if 'title' in row['_source']:
                        yield row['_source']
                page_no = page_no + 1
                logger.info('page %s/%s, total %s/%s' % (page_no, total_pages, total, total_size))
            except Exception as e:
                logger.exception(e)
                break

    def get_data_by_keyword(self, keyword, page=0, size=200, limit=None, country=None):
        query = {
            "match": {
                "title": {"query": keyword,
                          "operator": "and"
                          }
            }
        }

        ps = []

        while True:
            offset = page * size
            params = {
                'index': self.index_name,
                'from_': offset,
                'size': size,
                'body': {
                    'query': query
                }
            }

            if country is not None:
                params['doc_type'] = country

            # print params
            data = self.es_client.search(**params)

            if data['hits']['total'] == 0:
                break

            for row in data['hits']['hits']:
                asin = row['_source']['asin']
                if 'title' in row['_source']:
                    title = row['_source']['title']
                    brand = row['_source']['brand'] if 'brand' in row['_source'] else None
                    ps.append({'asin': asin, 'title': title, 'brand': brand})

            page = page + 1
            if limit is not None and len(ps) >= limit:
                break
            if data['hits']['total'] <= page * size:
                break

        return ps

    def remove_existed(self, asins):
        data = self.get_data(asins)
        for row in data['hits']['hits']:
            asin = row['_source']['asin']
            if 'title' in row['_source']:
                title = row['_source']['title']
                if len(title) > 0:
                    asins.remove(asin)
        return asins

    def bulk_add_data(self, asin, payload, op_type='index', region="US"):
        region = region.upper()
        act = dict(
            _op_type=op_type,
            _index=self.index_name,
            _id=asin,
            _type=region.lower(),
        )

        if op_type == 'update':
            act['doc'] = dict()
            for i in payload:
                act['doc'][i] = payload[i]
        else:
            for i in payload:
                act[i] = payload[i]

        # print act
        self.elastic_actions.append(act)

        if len(self.elastic_actions) >= self.bulk_length:
            self.process_bulk()

    def process_bulk(self):
        try:
            helpers.bulk(self.es_client.esclient, self.elastic_actions)
        except Exception as e:
            logger.exception(e)
            if 'blocked by' in traceback.format_exc():
                self.fix_read_only_settings()
                helpers.bulk(self.es_client.esclient, self.elastic_actions)
        self.elastic_actions = []

    def add_product_index(self, asin, payload, region="US"):
        region = region.upper()
        self.es_client.esclient.index("product", "product", payload, id="%s-%s" % (asin, region))

    def fix_read_only_settings(self):
        payload = {
            'index': {
                'blocks': {
                    'read_only_allow_delete': "false"
                }
            }
        }
        url = "http://" + self.host + "/" + self.index_name + "/_settings"
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        requests.put(url, json=payload, headers=headers)
