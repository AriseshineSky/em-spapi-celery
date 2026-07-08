# -*- coding: utf-8 -*-

import os

from em_celery.scheduling.kombu_priority_patch import (  # noqa: F401
    apply_kombu_priority_patch,
    broker_transport_options,
)
from em_celery.scheduling.priority import (
    PRIORITY_BULK,
    user_to_broker_priority,
)

# Task
task_ignore_result = True
task_store_errors_even_if_ignored = False
task_track_started = False
task_acks_late = True
task_reject_on_worker_lost = True
task_create_missing_queues = True
task_default_priority = user_to_broker_priority(PRIORITY_BULK)
task_queue_max_priority = 9

# Worker
broker_url = os.getenv('BROKER_URL', '')
broker_transport_options = broker_transport_options()
worker_prefetch_multiplier = 1

# Logging — stdout goes to journald when run under systemd (Celery best practice).
worker_hijack_root_logger = False
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = (
  '[%(asctime)s: %(levelname)s/%(processName)s] '
  '[%(task_name)s(%(task_id)s)] %(message)s'
)

# Events
worker_send_task_events = False
task_send_sent_event = False


def _apply_config_defaults():
  """Load broker_url from config.ini when BROKER_URL is unset."""
  global broker_url
  if broker_url:
    return
  from em_celery import get_broker_url
  broker_url = get_broker_url()


_apply_config_defaults()
