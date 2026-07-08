# -*- coding: utf-8 -*-
"""Central path resolution for config, logs, and runtime data."""

from __future__ import annotations

import os

_EM_CELERY_HOME = os.path.join('~', '.em_celery')
_CONFIG_FILE = os.path.join(_EM_CELERY_HOME, 'config.ini')
_LOG_DIR = os.path.join(_EM_CELERY_HOME, 'logs')
_DATA_DIR = os.path.join(_EM_CELERY_HOME, 'data')


def _expand(path: str) -> str:
  return os.path.abspath(os.path.expanduser(path))


def config_path() -> str:
  """Return ~/.em_celery/config.ini."""
  return _expand(_CONFIG_FILE)


def log_dir() -> str:
  """Directory for rotating CLI/sender log files."""
  value = os.getenv('EM_SPAPI_CELERY_LOG_DIR')
  if value:
    return _expand(value)
  return _expand(_LOG_DIR)


def data_dir() -> str:
  """Directory for runtime files (ASIN lists, checkpoints, etc.)."""
  value = os.getenv('EM_SPAPI_CELERY_DATA_DIR')
  if value:
    return _expand(value)
  return _expand(_DATA_DIR)
