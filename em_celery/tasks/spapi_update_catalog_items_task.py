# -*- coding: utf-8 -*-

import json
import os

import sentry_sdk
from sp_api.base.exceptions import *

from em_tasks.tasks.spapi_update_catalog_items_task import SpapiUpdateCatalogItemsTask
from em_tasks.spapi import exceptions_to_retry, exceptions_not_retry
# from sp_api.base.exceptions import (
#   SellingApiForbiddenException,
#   SellingApiException
# )

from celery.exceptions import Ignore
from celery.exceptions import Reject
from celery.utils.log import get_task_logger

from em_celery import sentry_enabled
from em_celery.tasks.base import BaseTask
from em_celery.tasks.worker_meta import build_worker_meta
from em_celery.worker import app

logger = get_task_logger(__name__)

@app.task(base=BaseTask, bind=True, acks_late=True, rate_limit='1/s')
def spapi_update_catalog_items(self, marketplace, asins, ttl=168, force=False, callback=None):
  task = SpapiUpdateCatalogItemsTask(self.spapi, self.product_service, marketplace, asins, worker=build_worker_meta(self.request))
  try:
    task.run()
  except SellingApiForbiddenException as e:
    logger.exception(e)
    app.control.broadcast('shutdown', destination=[self.request.hostname])
    try:
      self.bot.send_message(
        self.group_chat_id,
        "[SellingApiForbidden] Host: {}, API: GetCatalogItems, Error: {}\n".format(self.request.hostname, str(e))
      )
    except:
      pass

    raise Reject(str(e), requeue=True)
  except exceptions_to_retry as e:
    raise Reject(str(e), requeue=True)
  except exceptions_not_retry as e:
    if sentry_enabled:
      sentry_sdk.capture_exception(e)

    logger.exception(e)
    raise Ignore()
  except Exception as e:
    if sentry_enabled:
      sentry_sdk.capture_exception(e)

    logger.exception(e)
    raise Ignore()
