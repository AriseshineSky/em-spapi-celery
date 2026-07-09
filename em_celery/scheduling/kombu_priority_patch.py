# -*- coding: utf-8 -*-
"""Celery Redis broker transport options for native priority queues."""

from __future__ import annotations

from em_celery.scheduling.priority import REDIS_PRIORITY_SEP, REDIS_PRIORITY_STEPS


def broker_transport_options():
    """Shared Redis transport options for producers and workers.

    Matches Celery docs: ``priority_steps`` + ``sep: ":"`` + ``queue_order_strategy``.
    Priority 0 maps to the base queue name (highest); 9 maps to ``queue:9`` (lowest).
    """
    return {
        "priority_steps": REDIS_PRIORITY_STEPS,
        "sep": REDIS_PRIORITY_SEP,
        "queue_order_strategy": "priority",
    }
