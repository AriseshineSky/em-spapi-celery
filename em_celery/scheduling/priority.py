# -*- coding: utf-8 -*-
"""Task priority for Redis broker (Celery/Kombu native semantics).

Celery Redis priority (see routing docs):

- **0 = highest** → Redis list ``SpapiItemOffersUpdate_US`` (no suffix)
- **9 = lowest (bulk)** → ``SpapiItemOffersUpdate_US:9``

Workers consume sub-queues in ``priority_steps`` order (0 first, 9 last) with no patch.
"""

PRIORITY_CRITICAL = 0
PRIORITY_HIGH = 2
PRIORITY_NORMAL = 5
PRIORITY_LOW = 7
PRIORITY_BULK = 9

PRIORITY_MIN = 0
PRIORITY_MAX = 9

PRIORITY_NAMES = {
    PRIORITY_CRITICAL: "critical",
    PRIORITY_HIGH: "high",
    PRIORITY_NORMAL: "normal",
    PRIORITY_LOW: "low",
    PRIORITY_BULK: "bulk",
}

# Must match ``broker_transport_options['sep']`` in worker settings.
REDIS_PRIORITY_SEP = ":"
REDIS_PRIORITY_STEPS = list(range(10))
# Kombu BRPOP / RPOP order: base queue (0) first, then :1 … :9.
REDIS_BROKER_CONSUME_ORDER = list(range(10))


def normalize_user_priority(priority):
    """Clamp user priority to 0–9 (0 = highest, 9 = lowest)."""
    if priority is None:
        return PRIORITY_NORMAL
    try:
        value = int(priority)
    except (TypeError, ValueError):
        return PRIORITY_NORMAL
    return max(PRIORITY_MIN, min(PRIORITY_MAX, value))


def user_to_broker_priority(priority):
    """Map user priority to Celery Redis broker priority (same number)."""
    return normalize_user_priority(priority)


def broker_to_user_priority(priority):
    """Map Redis broker priority back to user-facing priority."""
    try:
        broker = int(priority)
    except (TypeError, ValueError):
        return PRIORITY_NORMAL
    broker = max(PRIORITY_MIN, min(PRIORITY_MAX, broker))
    return broker


def base_queue_name(queue_name, sep=REDIS_PRIORITY_SEP):
    """Strip a trailing ``:0``–``:9`` suffix so workers bind to the logical queue."""
    if sep not in queue_name:
        return queue_name
    base, _, suffix = queue_name.rpartition(sep)
    if suffix.isdigit() and PRIORITY_MIN <= int(suffix) <= PRIORITY_MAX:
        return base
    return queue_name


def iter_redis_priority_queue_keys(
    queue_name,
    sep=REDIS_PRIORITY_SEP,
    priority_steps=None,
):
    """Yield Redis list keys for all priority sub-queues (highest first: base, :1, …, :9)."""
    queue_name = base_queue_name(queue_name, sep=sep)
    steps = (
        REDIS_BROKER_CONSUME_ORDER
        if priority_steps is None
        else priority_steps
    )
    for step in steps:
        if step == 0:
            yield queue_name
        else:
            yield "{}{}{}".format(queue_name, sep, step)


def redis_priority_queue_depth(redis_client, queue_name, **kwargs):
    """Total pending messages across all priority sub-queues."""
    total = 0
    for key in iter_redis_priority_queue_keys(queue_name, **kwargs):
        try:
            total += int(redis_client.llen(key))
        except Exception:
            continue
    return total
