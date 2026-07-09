# -*- coding: utf-8 -*-
"""Integration test: Redis priority sub-queues consumed highest-first (local broker only)."""

from __future__ import annotations

import os

import pytest
import redis
from kombu import Connection

from em_celery.scheduling.kombu_priority_patch import broker_transport_options
from em_celery.scheduling.priority import iter_redis_priority_queue_keys
from em_celery.scheduling.send import dispatch_task
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers

TEST_BROKER = os.getenv("TEST_BROKER_URL", "redis://127.0.0.1:6379/15")
TEST_QUEUE = "SpapiItemOffersUpdate_ZZ"


@pytest.fixture
def local_broker():
    client = redis.Redis.from_url(TEST_BROKER)
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip(f"Redis not available at {TEST_BROKER}")

    for key in iter_redis_priority_queue_keys(TEST_QUEUE):
        client.delete(key)

    yield client

    for key in iter_redis_priority_queue_keys(TEST_QUEUE):
        client.delete(key)


def test_enqueue_maps_priority_to_redis_suffix(local_broker):
    conn = Connection(TEST_BROKER, transport_options=broker_transport_options())

    dispatch_task(
        spapi_update_item_offers,
        args=("zz", ["BULK001"], "new"),
        queue=TEST_QUEUE,
        connection=conn,
        priority=9,
    )
    dispatch_task(
        spapi_update_item_offers,
        args=("zz", ["HIGH001"], "new"),
        queue=TEST_QUEUE,
        connection=conn,
        priority=0,
    )

    assert local_broker.llen(f"{TEST_QUEUE}:9") == 1
    assert local_broker.llen(TEST_QUEUE) == 1


def test_worker_pops_high_priority_before_bulk(local_broker):
    conn = Connection(TEST_BROKER, transport_options=broker_transport_options())

    # Bulk first, critical second — consumption must still prefer base queue (priority 0).
    dispatch_task(
        spapi_update_item_offers,
        args=("zz", ["BULK001"], "new"),
        queue=TEST_QUEUE,
        connection=conn,
        priority=9,
    )
    dispatch_task(
        spapi_update_item_offers,
        args=("zz", ["HIGH001"], "new"),
        queue=TEST_QUEUE,
        connection=conn,
        priority=0,
    )

    with conn.channel() as channel:
        channel._get(TEST_QUEUE)
        assert local_broker.llen(TEST_QUEUE) == 0
        assert local_broker.llen(f"{TEST_QUEUE}:9") == 1

        channel._get(TEST_QUEUE)
        assert local_broker.llen(f"{TEST_QUEUE}:9") == 0
