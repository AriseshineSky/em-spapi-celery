# -*- coding: utf-8 -*-
"""Celery Redis broker transport options for native priority queues."""

from __future__ import annotations

from em_celery.scheduling.priority import REDIS_PRIORITY_SEP, REDIS_PRIORITY_STEPS


def broker_transport_options():
    """Shared Redis transport options for producers and workers.

    Matches Celery docs: ``priority_steps`` + ``sep: ":"`` + ``queue_order_strategy``.
    Priority 0 maps to the base queue name (highest); 9 maps to ``queue:9`` (lowest).

    ``round_robin`` rotates marketplace queues after each consume so same-priority
    sites share fairly; within one BRPOP, all priority-0 keys still precede ``:9``.
    """
    return {
        "priority_steps": REDIS_PRIORITY_STEPS,
        "sep": REDIS_PRIORITY_SEP,
        "queue_order_strategy": "round_robin",
    }
