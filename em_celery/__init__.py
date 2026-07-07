# -*- coding: utf-8 -*-

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pydispatch import dispatcher

import sentry_sdk

from dropshipping.signals import invalid_asin
from dropshipping.utils.offer_services import EsOfferService
from em_tasks.spapi import Spapi
from em_tasks.utils.product_service import ProductService
from em_celery.utils.config_loaders import IniConfigLoader
from em_celery.paths import config_path as resolve_config_path
from em_celery.utils.telegram_bot import TelegramBot


logger = logging.getLogger('em_celery.' + __name__)
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

_cfg = None

def get_config():
  global _cfg
  if _cfg is None:
    config = IniConfigLoader(resolve_config_path(), False)
    _cfg = config.load()

  return _cfg

def get_broker_url():
  url = os.getenv('BROKER_URL')
  if url:
    return url
  return get_config().get('celery', {}).get('broker_url', '')

def get_product_service():
  config = get_config()
  product_cfg = config['product_service']
  return ProductService(
    product_cfg['host'], product_cfg['port'], product_cfg['user'], product_cfg['password'])

def get_offer_service():
  config = get_config()
  offer_cfg = config['offer_service']
  return EsOfferService(
    offer_cfg['host'], offer_cfg['port'], offer_cfg['user'], offer_cfg['password'])

def get_offer_service_config():
  config = get_config()
  return config['offer_service']

def get_amz_broker_url():
  return get_broker_url() or get_config().get('broker_url', {}).get('amz', None)

def get_emp_offer_filter_config(marketplace):
  filter_cond = {
    'rating': 60,
    'feedback': 5,
    'domestic': True,
    'shipping_time': 7,
    'subcondition': 70,
    'expire_hour': 120,
  }

  config = get_config()
  amz_offer_filter_cfg = config.get('emp.offer.filter.{}'.format(marketplace), config.get('emp.offer.filter', None))
  if amz_offer_filter_cfg:
    filter_cond = {
      'rating': int(amz_offer_filter_cfg.get('rating', 60)),
      'feedback': int(amz_offer_filter_cfg.get('feedback', 5)),
      'domestic': bool(amz_offer_filter_cfg.get('domestic', True)),
      'shipping_time': int(amz_offer_filter_cfg.get('shipping_time', 7)),
      'subcondition': int(amz_offer_filter_cfg.get('subcondition', 70)),
      'expire_hour': int(amz_offer_filter_cfg.get('expire_hour', 120)),
    }

  return filter_cond

def get_amz_offer_filter_config(marketplace):
  filter_cond = {
    'rating': 60,
    'feedback': 5,
    'domestic': True,
    'shipping_time': 7,
    'subcondition': 70,
    'expire_hour': 120,
  }

  config = get_config()
  amz_offer_filter_cfg = config.get('amz.offer.filter.{}'.format(marketplace), config.get('amz.offer.filter', None))
  if amz_offer_filter_cfg:
    filter_cond = {
      'rating': int(amz_offer_filter_cfg.get('rating', 60)),
      'feedback': int(amz_offer_filter_cfg.get('feedback', 5)),
      'domestic': bool(amz_offer_filter_cfg.get('domestic', True)),
      'shipping_time': int(amz_offer_filter_cfg.get('shipping_time', 7)),
      'subcondition': int(amz_offer_filter_cfg.get('subcondition', 70)),
      'expire_hour': int(amz_offer_filter_cfg.get('expire_hour', 120)),
    }

  return filter_cond

def get_spapi():
  config = get_config()
  spapi_cfg = config['spapi']
  credentials = {
    'refresh_token': spapi_cfg['lwa_refresh_token'],
    'lwa_app_id': spapi_cfg['lwa_client_id'],
    'lwa_client_secret': spapi_cfg['lwa_client_secret'],
    'aws_access_key': spapi_cfg['aws_access_key'],
    'aws_secret_key': spapi_cfg['aws_secret_key']
  }

  return Spapi(credentials)

def get_bot():
  config = get_config()
  telegram_cfg = config.get('telegram', {})
  api_token = telegram_cfg.get('api_token') or os.getenv('TELEGRAM_BOT_TOKEN')
  if not api_token:
    return None
  return TelegramBot(api_token)

def get_group_chat_id():
  config = get_config()
  telegram_cfg = config.get('telegram', {})
  return telegram_cfg.get('group_chat_id') or os.getenv('TELEGRAM_GROUP_CHAT_ID', '')

def save_error_asins(asin, country, errors='', ignore_exc=True):
  logger.warning('Invalid ASIN %s (%s): %s', asin, country, errors)

dispatcher.connect(save_error_asins, signal=invalid_asin)

sentry_enabled = False
config = get_config()
sentry_cfg = config.get('sentry', {})
dsn = sentry_cfg.get('dsn', None)
traces_sample_rate = sentry_cfg.get('traces_sample_rate', 0.5)
profiles_sample_rate = sentry_cfg.get('profiles_sample_rate', 0.1)
if dsn:
  sentry_enabled = True

  sentry_sdk.init(
    dsn=dsn,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=traces_sample_rate,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=profiles_sample_rate,
  )
