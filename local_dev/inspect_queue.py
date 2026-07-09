#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspect or purge Celery Redis queue lengths for SP-API catalog/offer tasks.

Celery (Redis backend) stores pending messages in lists named after the queue.
Priority tasks use suffix sub-keys ``:1``–``:9``; priority 0 (highest) uses the base name.
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    import redis
except ImportError:
    print("Install redis: pip install redis", file=sys.stderr)
    raise

from em_celery.scheduling.priority import (
    iter_redis_priority_queue_keys,
    redis_priority_queue_depth,
)


def queue_names(marketplace: str) -> tuple[str, str]:
    mp = marketplace.upper()
    return (
        f"SpapiCatalogItemsUpdate_{mp}",
        f"SpapiItemOffersUpdate_{mp}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SP-API Celery queue lengths.")
    parser.add_argument(
        "--broker",
        default=os.getenv("BROKER_URL", "redis://127.0.0.1:6379/0"),
        help="Redis broker URL",
    )
    parser.add_argument("--marketplace", default="us", help="Marketplace code")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-priority sub-queue lengths",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Delete all pending messages in both queues (destructive)",
    )
    args = parser.parse_args()

    catalog_q, offers_q = queue_names(args.marketplace)
    client = redis.Redis.from_url(args.broker)

    try:
        client.ping()
    except redis.ConnectionError as exc:
        print(f"Cannot connect to broker {args.broker}: {exc}", file=sys.stderr)
        return 1

    queues = [catalog_q, offers_q]
    for name in queues:
        total = redis_priority_queue_depth(client, name)
        print(f"{name}: {total} pending message(s)")
        if args.verbose:
            for key in iter_redis_priority_queue_keys(name):
                length = client.llen(key)
                if length:
                    print(f"  {key}: {length}")

    if args.purge:
        for name in queues:
            deleted = 0
            for key in iter_redis_priority_queue_keys(name):
                deleted += client.delete(key)
            print(f"purged {name}: deleted={deleted} key(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
