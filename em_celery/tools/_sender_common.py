# -*- coding: utf-8 -*-
"""Shared Click options and logging for task sender CLIs."""

import click

from em_celery.runtime import resolve_broker_url, setup_cli_logging


def broker_option(**kwargs):
  defaults = dict(
    type=str,
    default=None,
    help='Celery broker URL (default: BROKER_URL or [celery] broker_url in config.ini).',
  )
  defaults.update(kwargs)
  return click.option('-b', '--broker_url', **defaults)


def configure_sender(logger_module: str, log_basename: str):
  """Call at the start of a sender CLI after parsing args."""
  setup_cli_logging(logger_module, log_basename)


def normalize_broker(broker_url: str | None) -> str:
  return resolve_broker_url(broker_url)
