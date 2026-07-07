# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from __future__ import absolute_import
import time

from functools import wraps

from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch.exceptions import RequestError
from elasticsearch.exceptions import NotFoundError
from elasticsearch.exceptions import ConnectionTimeout
from elasticsearch.exceptions import ConnectionError
from elasticsearch.exceptions import SSLError
from elasticsearch.exceptions import TransportError
from elasticsearch.exceptions import ElasticsearchException
from elasticsearch.exceptions import ImproperlyConfigured
from elasticsearch.exceptions import AuthenticationException
from elasticsearch.exceptions import AuthorizationException

from pydispatch.robust import sendRobust

from dropshipping.signals import es_unavailable
from dropshipping import logger


class EsServerError(Exception):
    pass


class EsClientError(Exception):
    pass


class EsUnauthorizedError(Exception):
    pass


def es_retry(func):
    @wraps(func)
    def wrapper_es_retry(*args, **kwargs):
        val = None
        num_retries = 3

        while num_retries > 0:
            try:
                val = func(*args, **kwargs)
                break
            except NotFoundError as e:
                break
            except RequestError as e:
                raise EsClientError(str(e))
            except (ImproperlyConfigured, AuthenticationException, AuthorizationException) as e:
                raise EsUnauthorizedError(str(e))
            except (ConnectionTimeout, ConnectionError, SSLError, TransportError) as e:
                num_retries -= 1
                if num_retries <= 0:
                    raise EsServerError(str(e))

                time.sleep(1)
            except ElasticsearchException as e:
                num_retries -= 1
                if num_retries <= 0:
                    raise e

                status_code = getattr(e, 'status_code', None)
                if status_code == 'N/A':
                    time.sleep(1)
            except Exception as e:
                num_retries -= 1
                if num_retries <= 0:
                    raise e

        return val

    return wrapper_es_retry


class EsService(object):
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

        self.esclient = Elasticsearch(
            hosts=host, port=port, http_auth=(user, password),
            retry_on_timeout=True)
        self.active = True

    def is_active(self):
        return self.active

    def deactivate(self, reason=''):
        self.active = False

        # Notify elasticsearch failure
        payload = {
            'host': self.host,
            'port': self.port,
            'reason': reason
        }
        return sendRobust(signal=es_unavailable, sender=self, **payload)

    def search(self, *args, **kwargs):
        if not self.is_active():
            return False

        wrapped_search = es_retry(self.esclient.search)
        try:
            result = wrapped_search(*args, **kwargs)
        except EsServerError as e:
            logger.exception(e)
            result = False
        except EsClientError as e:
            logger.exception(e)
            result = None
        except EsUnauthorizedError as e:
            logger.exception(e)
            self.deactivate(str(e))
            result = False
        except Exception as e:
            logger.exception(e)
            result = None

        return result

    def _bulk(self, *args, **kwargs):
        if not self.is_active():
            return False

        opts = {'max_retries': 3}
        opts.update(kwargs)

        wrapped_bulk = es_retry(helpers.bulk)
        try:
            result = wrapped_bulk(self.esclient, *args, **opts)
        except EsServerError as e:
            logger.exception(e)
            result = False
        except EsClientError as e:
            logger.exception(e)
            result = None
        except EsUnauthorizedError as e:
            logger.exception(e)
            self.deactivate(str(e))
            result = False
        except Exception as e:
            logger.exception(e)
            result = None

        return result

    def _count(self, **kwargs):
        if not self.is_active():
            return False

        wrapped_count = es_retry(self.esclient.count)
        try:
            result = wrapped_count(**kwargs)
        except EsServerError as e:
            logger.exception(e)
            result = False
        except EsClientError as e:
            logger.exception(e)
            result = None
        except EsUnauthorizedError as e:
            logger.exception(e)
            self.deactivate(str(e))
            result = False
        except Exception as e:
            logger.exception(e)
            result = None

        return result

    def _scan(self, *args, **kwargs):
        if not self.is_active():
            return False

        wrapped_scan = es_retry(helpers.scan)
        try:
            for item in wrapped_scan(self.esclient, *args, **kwargs):
                yield item
        except EsServerError as e:
            logger.exception(e)
        except EsClientError as e:
            logger.exception(e)
        except EsUnauthorizedError as e:
            logger.exception(e)
            self.deactivate(str(e))
        except Exception as e:
            logger.exception(e)
