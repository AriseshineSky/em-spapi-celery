#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L1 smoke test: dispatch catalog/offer tasks to Redis without ES or SP-API.

Does not use the official sender CLI (which connects to ES on init).
Run inspect_queue.py afterwards to confirm messages landed in the broker.
"""

from __future__ import annotations

import argparse
import os
import sys

from kombu import Connection


def _broker_url(explicit: str | None) -> str:
    url = explicit or os.getenv("BROKER_URL", "redis://127.0.0.1:6379/0")
    if not url:
        print("Set BROKER_URL or pass --broker", file=sys.stderr)
        sys.exit(1)
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch sample SP-API Celery tasks.")
    parser.add_argument(
        "--broker",
        default=None,
        help="Celery broker URL (default: BROKER_URL or redis://127.0.0.1:6379/0)",
    )
    parser.add_argument("--marketplace", default="us", help="Marketplace code, e.g. us")
    parser.add_argument(
        "--asins",
        nargs="+",
        default=["B0D1XD1ZV3"],
        help="ASINs to include in each dispatched task",
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Only dispatch spapi_update_catalog_items",
    )
    parser.add_argument(
        "--offers-only",
        action="store_true",
        help="Only dispatch spapi_update_item_offers",
    )
    args = parser.parse_args()

    broker = _broker_url(args.broker)
    marketplace = args.marketplace.lower()
    mp_upper = marketplace.upper()
    asins = list(args.asins)

    dispatch_catalog = not args.offers_only
    dispatch_offers = not args.catalog_only

    # Import after argparse so --help works even if em_celery deps are missing.
    from em_celery.tasks.spapi_update_catalog_items_task import spapi_update_catalog_items
    from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers

    conn = Connection(broker)
    dispatched = []

    if dispatch_catalog:
        queue = f"SpapiCatalogItemsUpdate_{mp_upper}"
        spapi_update_catalog_items.apply_async(
            args=(marketplace, asins),
            queue=queue,
            connection=conn,
        )
        dispatched.append(f"catalog -> {queue} asins={asins}")

    if dispatch_offers:
        queue = f"SpapiItemOffersUpdate_{mp_upper}"
        spapi_update_item_offers.apply_async(
            args=(marketplace, asins, "new"),
            queue=queue,
            connection=conn,
        )
        dispatched.append(f"offer -> {queue} asins={asins} condition=new")

    for line in dispatched:
        print(f"OK: dispatched {line}")
    print(f"Broker: {broker}")
    print("Next: python local_dev/inspect_queue.py --broker", broker, "--marketplace", marketplace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
