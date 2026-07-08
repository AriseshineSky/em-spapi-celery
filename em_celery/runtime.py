# -*- coding: utf-8 -*-
"""Runtime helpers shared by workers, senders, and deployment."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from em_celery.paths import config_path, log_dir
from em_celery.scheduling.priority import base_queue_name

_LOG_FORMAT = '%(asctime)s %(name)s [%(levelname)s]: %(message)s'
_CONFIGURED_LOGGERS: set[str] = set()


def resolve_broker_url(cli_value: str | None = None) -> str:
  """Broker URL from CLI flag, BROKER_URL env, or config [celery] section."""
  if cli_value:
    return cli_value

  env_url = os.getenv('BROKER_URL')
  if env_url:
    return env_url

  from em_celery import get_config

  cfg_url = get_config().get('celery', {}).get('broker_url')
  if cfg_url:
    return cfg_url

  raise SystemExit(
    'Broker URL is required: set BROKER_URL, [celery] broker_url in config.ini, '
    'or pass -b/--broker_url.'
  )


def setup_cli_logging(logger_name: str, log_basename: str | None = None) -> logging.Logger:
  """Configure stdout + optional rotating file logging for CLI tools.

  Under systemd, stdout is enough (journald). Set EM_SPAPI_CELERY_LOG_TO_FILE=0
  to skip file handlers.
  """
  logger = logging.getLogger(logger_name)
  if logger_name in _CONFIGURED_LOGGERS:
    return logger

  level_name = os.getenv('EM_SPAPI_CELERY_LOG_LEVEL', 'INFO').upper()
  level = getattr(logging, level_name, logging.INFO)
  logger.setLevel(level)

  if not logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(stream_handler)

  write_files = os.getenv('EM_SPAPI_CELERY_LOG_TO_FILE', '1') not in ('0', 'false', 'no')
  if write_files and log_basename:
    directory = log_dir()
    os.makedirs(directory, exist_ok=True)
    log_path = os.path.join(directory, log_basename)
    file_handler = RotatingFileHandler(
      log_path, maxBytes=20 * 1024 ** 2, backupCount=5,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(file_handler)

  _CONFIGURED_LOGGERS.add(logger_name)
  return logger


def get_worker_settings(worker_type: str) -> dict[str, str]:
  """Worker queues/concurrency from /etc/conf.d/em_celery environment variables."""
  if worker_type not in ('catalog', 'offer'):
    raise ValueError(f'worker_type must be catalog or offer, got {worker_type!r}')

  default_queues = {
    'catalog': 'SpapiCatalogItemsUpdate_US',
    'offer': 'SpapiItemOffersUpdate_US',
  }

  queues = _normalize_worker_queues(
    _env_queues(worker_type) or default_queues[worker_type]
  )
  concurrency = _env_concurrency(worker_type) or '2'
  loglevel = (
    os.getenv('CELERY_LOGLEVEL')
    or os.getenv('EM_SPAPI_CELERY_LOG_LEVEL')
    or 'INFO'
  )

  return {
    'queues': queues,
    'concurrency': concurrency,
    'loglevel': loglevel,
    'node_name': f'{worker_type}-worker@%h',
  }


def _env_queues(worker_type: str) -> str | None:
  """CELERY_CATALOG_QUEUES / CELERY_OFFER_QUEUES, or split CELERY_QUEUES."""
  prefix = worker_type.upper()
  specific = os.getenv(f'CELERY_{prefix}_QUEUES')
  if specific:
    return specific.strip()

  combined = os.getenv('CELERY_QUEUES')
  if not combined:
    return None

  catalog, offer = _split_queues_by_type(combined)
  return catalog if worker_type == 'catalog' else offer


def _env_concurrency(worker_type: str) -> str | None:
  prefix = worker_type.upper()
  specific = os.getenv(f'CELERY_{prefix}_CONCURRENCY')
  if specific:
    return specific.strip()
  value = os.getenv('CELERY_CONCURRENCY')
  return value.strip() if value else None


def _normalize_worker_queues(combined: str) -> str:
  """Strip ``:0``–``:9`` suffixes; Kombu handles priority sub-queues on the base name."""
  names: list[str] = []
  seen: set[str] = set()
  for raw in combined.split(','):
    queue = base_queue_name(raw.strip())
    if not queue or queue in seen:
      continue
    seen.add(queue)
    names.append(queue)
  return ','.join(names)


def _split_queues_by_type(combined: str) -> tuple[str | None, str | None]:
  """Split combined queue list into catalog / offer by name prefix."""
  if not combined:
    return None, None

  catalog: list[str] = []
  offer: list[str] = []
  for raw in combined.split(','):
    queue = base_queue_name(raw.strip())
    if not queue:
      continue
    if queue.startswith('SpapiCatalogItemsUpdate_'):
      catalog.append(queue)
    elif queue.startswith('SpapiItemOffersUpdate_'):
      offer.append(queue)

  return (
    ','.join(catalog) if catalog else None,
    ','.join(offer) if offer else None,
  )


def deployment_summary() -> dict[str, str]:
  """Useful paths for ops / debugging."""
  from em_celery.paths import data_dir
  return {
    'config': config_path(),
    'log_dir': log_dir(),
    'data_dir': data_dir(),
    'broker_env': os.getenv('BROKER_URL', ''),
  }
