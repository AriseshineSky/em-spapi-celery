import copy
import time
import sys
import json

from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch.client import IndicesClient
from elasticsearch.exceptions import RequestError
from elasticsearch.exceptions import NotFoundError
from elasticsearch.exceptions import ConnectionTimeout
from elasticsearch.exceptions import ConnectionError
from elasticsearch.exceptions import SSLError
from elasticsearch.exceptions import TransportError
from elasticsearch.exceptions import ElasticsearchException

from dropshipping.utils.es_service import es_retry

from em_tasks import logger


class ProductService(object):
  def __init__(self, host, port, user, password, max_retry=3):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.max_retry = max_retry

    self.esclient = Elasticsearch(hosts=host, port=port, http_auth=(user, password))

  def _needs_shard_defaults(self, settings_section):
    if not isinstance(settings_section, dict):
      return True
    if "number_of_shards" in settings_section or "number_of_replicas" in settings_section:
      return False
    idx = settings_section.get("index")
    if isinstance(idx, dict) and (
        "number_of_shards" in idx or "number_of_replicas" in idx
    ):
      return False
    return True

  def _apply_default_shard_settings(self, body):
    """Use one primary and no replicas unless caller set shard/replica counts (saves cluster shard budget)."""
    body = copy.deepcopy(body) if body else {}
    body.setdefault("settings", {})
    s = body["settings"]
    if self._needs_shard_defaults(s):
      s["number_of_shards"] = 1
      s["number_of_replicas"] = 0
    return body

  def ensure_indice(self, indice_name, settings=None):
    ic = IndicesClient(self.esclient)
    if ic.exists(indice_name):
      if settings and settings.get("mappings"):
        try:
          ic.put_mapping(body=settings["mappings"], index=indice_name)
        except RequestError as e:
          logger.debug("put_mapping skipped for %s: %s", indice_name, e)
      return True

    create_body = self._apply_default_shard_settings(settings)
    try:
      ic.create(indice_name, body=create_body)
    except RequestError as e:
      logger.warning(
        "Could not create Elasticsearch index %s: %s",
        indice_name,
        e,
      )
      return False

    return ic.exists(indice_name)

  def search_products(self, indice_name, product_ids, options={}):
    if not isinstance(product_ids, list):
      product_ids = [product_ids]

    query = {"terms": {"_id": product_ids}}

    params = {
      'index': indice_name,
      'from_': 0,
      'size': len(product_ids),
      'body': {
        'query': query
      }
    }
    if options:
        params.update(options)

    wrapped_search = es_retry(self.esclient.search)
    resp = None
    try:
      resp = wrapped_search(**params)
    except:
      pass

    if resp is None:
      result = None
    elif resp == -1:
      result = False
    else:
      result = {}
      if "hits" in resp['hits']:
          for item in resp['hits']['hits']:
            result[item['_id']] = item['_source']

    return result

  def is_product_exist(self, indice_name, product_ids):
    if not isinstance(product_ids, list):
      product_ids = [product_ids]

    query = {"terms": {"_id": product_ids}}

    params = {
      'index': indice_name,
      'from_': 0,
      'size': len(product_ids),
      '_source': False,
      'body': {
        'query': query
      }
    }

    wrapped_search = es_retry(self.esclient.search)
    resp = None
    try:
      resp = wrapped_search(**params)
    except:
      pass

    if resp is None:
      result = None
    elif resp == -1:
      result = False
    else:
      result = {pid:False for pid in product_ids}
      if "hits" in resp['hits']:
          for item in resp['hits']['hits']:
            result[item['_id']] = True

    return result

  def custom_search(self, indice_name, options, from_=0, size=1000):
    params = {
      'index': indice_name,
      'from_': from_,
      'size': size,
      # 'body': {
      #   'query': query
      # }
    }
    if options:
      params.update(options)

    wrapped_search = es_retry(self.esclient.search)
    resp = None
    try:
      resp = wrapped_search(**params)
    except Exception as e:
      logger.exception(e)

    return resp

  def save_products(self, indice_name, products):
      """
      Save web crawled products to service.
      products : list
          The same as return value of search_products
      """
      if not isinstance(products, list):
        products = [products]

      service_products = []

      common_args = {
        '_op_type': 'index',
        '_index': indice_name,
        '_type': '_doc'
      }

      for product in products:
        service_product = dict()
        service_product.update(common_args)
        if 'product_id' not in product and '_id' not in product:
          continue

        if '_id' in product:
          service_product['_id'] = product.pop('_id')
        elif 'product_id' in product:
          service_product['_id'] = product['product_id']

        service_product['_source'] = product

        service_products.append(service_product)

      retry = self.max_retry
      while retry > 0:
        try:
          helpers.bulk(self.esclient, service_products, request_timeout=30)
          break
        except (ConnectionTimeout, ConnectionError, SSLError, TransportError):
          retry -= 1
          continue
        except Exception as e:
          raise e

  def load_products(self, indice_name, options = {}):
    params = {
      'index': indice_name,
      'doc_type': '_doc',
      'size': 1500,
      'query': {'query': {'match_all': {}}}
    }
    if options:
      params.update(options)

    wrapped_scan = es_retry(helpers.scan)
    try:
      for item in wrapped_scan(self.esclient, **params):
        record = None
        if '_source' in item and item['_source']:
          if isinstance(item['_source'], dict):
            record = item['_source']
          else:
            record = json.loads(item['_source'])

        yield (item['_id'], record)
    except Exception as e:
      logger.exception(e)

  def load_product_by_after_search(self, indice_name, cut_time="1999-01-01T00:00:00"):
    search_after_value = None

    while True:
      body = {
        "size": 1000,
        "sort": [
          {
            "time": {"order": "desc"},
          },
          {
            "_id": {"order": "desc"},
          }
        ],
        "query": {
          "range": {"time": {"gt": cut_time}}
        }
      }

      if search_after_value:
        body["search_after"] = search_after_value

      resp = self.esclient.search(index=indice_name, body=body)

      hits = resp["hits"]["hits"]
      if not hits:
        break

      for h in hits:
        product = h["_source"]
        yield product

      search_after_value = hits[-1]["sort"]

  def load_products_by_after_search(
    self,
    indice_name,
    cut_time="1999-01-01T00:00:01.722593+00:00",
    key="timestamp",
    label=None,
    label_field="label",
  ):
    search_after_value = None

    while True:
      range_clause = {"range": {key: {"gt": cut_time}}}
      if label:
        query = {
          "bool": {
            "must": [
              range_clause,
              {"term": {label_field: label}},
            ]
          }
        }
      else:
        query = range_clause

      body = {
        "size": 1000,
        "sort": [
          {
            key: {"order": "desc"},
          },
          {
            "_id": {"order": "desc"},
          }
        ],
        "query": query,
      }

      if search_after_value:
        body["search_after"] = search_after_value

      resp = self.esclient.search(index=indice_name, body=body)

      hits = resp["hits"]["hits"]
      if not hits:
        break

      for h in hits:
        asin = h["_source"]["asin"]
        yield asin, h["_source"]

      search_after_value = hits[-1]["sort"]

  def delete_products(self, indice_name, product_ids):
    actions = []
    for product_id in product_ids:
      actions.append({
        '_op_type': 'delete',
        '_index': indice_name,
        '_type': '_doc',
        '_id': product_id
      })

    retry = self.max_retry
    while retry > 0:
      try:
        helpers.bulk(self.esclient, actions, raise_on_error=False, request_timeout=30)
        break
      except (ConnectionTimeout, ConnectionError, SSLError, TransportError):
        retry -= 1
        continue
      except Exception as e:
        raise e
