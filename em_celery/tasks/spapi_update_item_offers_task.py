# -*- coding: utf-8 -*-

import json

import sentry_sdk
from sp_api.base.exceptions import *
from sp_api.auth.exceptions import AuthorizationError

from em_tasks.tasks.spapi_update_item_offers_task import SpapiUpdateItemOffersTask
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
from em_celery.worker import app

logger = get_task_logger(__name__)


@app.task(base=BaseTask, bind=True, acks_late=True, rate_limit='8/m')
def spapi_update_item_offers(self, marketplace, asins, condition='new', ttl=24, force=False, callback=None):
  task = SpapiUpdateItemOffersTask(
    self.spapi,
    self.offer_service,
    marketplace,
    asins,
    condition,
  )
  try:
    task.run()
  except (SellingApiForbiddenException, AuthorizationError) as e:
    logger.exception(e)
    app.control.broadcast('shutdown', destination=[self.request.hostname])
    try:
      self.bot.send_message(
        self.group_chat_id,
        "[SellingApiForbidden] Host: {}, API: GetItemOffersBatch\n".format(self.request.hostname)
      )
    except:
      pass

    raise Reject(str(e), requeue=True)
  except exceptions_to_retry as e:
    # TODO: Record rejected tasks
    self.rejected_tasks_cnt += 1
    if self.rejected_tasks_cnt > 250:
      try:
        message = "[SpapiItemOffersRejectedReset] Host: {}, API: GetItemOffersBatch, Error: {}\n".format(
          self.request.hostname, str(e))
        self.bot.send_message(self.group_chat_id, message)
      except:
        pass

      self.rejected_tasks_cnt = 0

    raise Reject(str(e), requeue=True)
  except exceptions_not_retry as e:
    # TODO: Record why not retry
    if sentry_enabled:
      sentry_sdk.capture_exception(e)

    logger.exception(e)
    raise Ignore()
  except Exception as e:
    if sentry_enabled:
      sentry_sdk.capture_exception(e)

    logger.exception(e)
    raise Ignore()
