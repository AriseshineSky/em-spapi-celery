# -*- coding: utf-8 -*-

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init
from celery.utils.log import get_logger

logger = get_logger(__name__)

app = Celery('em_celery')
app.config_from_object('em_celery.config')
app.autodiscover_tasks(['em_celery'], force=True)


@worker_process_init.connect
def _ensure_item_offers_product_indices_on_worker_fork(**kwargs):
  """Once per forked worker process; indices used when saving item-offers stats via ProductService."""
  try:
    from em_celery import get_product_service
    from em_tasks.tasks.spapi_update_item_offers_task import (
        ensure_item_offers_product_indices,
    )

    ensure_item_offers_product_indices(get_product_service())
  except Exception:
    logger.exception("ensure_item_offers_product_indices on worker_process_init failed")


if __name__ == '__main__':
    app.start()
