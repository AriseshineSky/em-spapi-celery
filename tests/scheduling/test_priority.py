# -*- coding: utf-8 -*-
"""Tests for Redis-backed Celery priority mapping."""

from em_celery.scheduling.priority import (
    PRIORITY_CRITICAL,
    PRIORITY_NORMAL,
    REDIS_BROKER_CONSUME_ORDER,
    base_queue_name,
    broker_to_user_priority,
    iter_redis_priority_queue_keys,
    normalize_user_priority,
    user_to_broker_priority,
)
from em_celery.scheduling.send import dispatch_task


class _FakeTask:
    last_priority = None

    def apply_async(self, args=None, kwargs=None, **options):
        _FakeTask.last_priority = options.get("priority")
        return object()


def test_user_priority_9_maps_to_broker_9():
    assert user_to_broker_priority(9) == 9
    assert user_to_broker_priority(PRIORITY_CRITICAL) == 9


def test_user_priority_0_maps_to_broker_0():
    assert user_to_broker_priority(0) == 0


def test_normal_priority_round_trip():
    assert user_to_broker_priority(PRIORITY_NORMAL) == 5
    assert broker_to_user_priority(5) == PRIORITY_NORMAL


def test_normalize_clamps():
    assert normalize_user_priority(99) == 9
    assert normalize_user_priority(-1) == 0
    assert normalize_user_priority(None) == PRIORITY_NORMAL


def test_dispatch_task_converts_priority():
    task = _FakeTask()
    dispatch_task(task, priority=9)
    assert task.last_priority == 9
    dispatch_task(task, priority=1)
    assert task.last_priority == 1


def test_redis_queue_keys_highest_suffix_first():
    keys = list(iter_redis_priority_queue_keys("SpapiItemOffersUpdate_US"))
    assert keys[0] == "SpapiItemOffersUpdate_US:9"
    assert keys[-1] == "SpapiItemOffersUpdate_US"
    assert len(keys) == 10


def test_broker_consume_order_checks_nine_first():
    assert REDIS_BROKER_CONSUME_ORDER[0] == 9
    assert REDIS_BROKER_CONSUME_ORDER[-1] == 0


def test_base_queue_name_strips_priority_suffix():
    assert base_queue_name("SpapiItemOffersUpdate_CA:9") == "SpapiItemOffersUpdate_CA"
    assert base_queue_name("SpapiItemOffersUpdate_CA") == "SpapiItemOffersUpdate_CA"


def test_broker_transport_options_use_ascending_steps():
    from em_celery.scheduling.kombu_priority_patch import broker_transport_options

    opts = broker_transport_options()
    assert opts["priority_steps"] == list(range(10))
