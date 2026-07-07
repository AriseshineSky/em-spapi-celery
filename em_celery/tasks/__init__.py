# -*- coding: utf-8 -*-
"""Celery task registry — explicit exports for autodiscover."""

from em_celery.tasks.spapi_update_catalog_items_task import spapi_update_catalog_items
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers

__all__ = [
  'spapi_update_catalog_items',
  'spapi_update_item_offers',
]
