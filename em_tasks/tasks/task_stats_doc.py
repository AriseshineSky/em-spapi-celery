# -*- coding: utf-8 -*-
"""Legacy-compatible task stats documents for Elasticsearch monitoring."""


def format_minute_iso(minute_bucket):
  return minute_bucket.isoformat()


def ms_to_seconds(value_ms):
  return round(float(value_ms) / 1000.0, 6)


def build_offer_stats_doc(
  *,
  doc_id,
  worker_id,
  marketplace,
  condition,
  minute_bucket,
  stats,
  task_count,
  spapi_success_count,
  fetch_gap_count,
):
  """Match legacy item_offers stats docs (stats_kind + *_s fields)."""
  minute_iso = format_minute_iso(minute_bucket)
  failed = int(stats["failed_asins"])

  return {
    "_id": doc_id,
    "stats_kind": "item_offers",
    "marketplace": marketplace,
    "condition": (condition or "new").lower(),
    "minute": minute_iso,
    "time": minute_iso,
    "worker": worker_id,
    "total_asins_requested": int(stats["num_asins"]),
    "with_offer_row_count": int(stats["successful_asins"]),
    "missing_offer_row_count": failed,
    "missing_offer_asin_unique_count": failed,
    "task_count": int(task_count),
    "task_duration_s": ms_to_seconds(stats["task_duration_ms"]),
    "spapi_duration_s": ms_to_seconds(stats["spapi_duration_ms"]),
    "api_failed": int(stats["api_failed"]),
    "avg_task_duration_s": ms_to_seconds(
      stats["task_duration_ms"] // task_count if task_count else 0
    ),
    "avg_spapi_duration_s": ms_to_seconds(
      stats["spapi_duration_ms"] // task_count if task_count else 0
    ),
    "avg_spapi_success_s": ms_to_seconds(
      stats["spapi_success_duration_ms"] // spapi_success_count if spapi_success_count else 0
    ),
    "avg_fetch_gap_s": ms_to_seconds(
      stats["fetch_gap_ms"] // fetch_gap_count if fetch_gap_count else 0
    ),
    "fetch_gap_s": ms_to_seconds(stats["fetch_gap_ms"]),
    "fetch_gap_count": int(fetch_gap_count),
    "spapi_success_count": int(spapi_success_count),
  }


def build_catalog_stats_doc(
  *,
  doc_id,
  worker_id,
  marketplace,
  minute_bucket,
  stats,
  task_count,
  spapi_success_count,
  fetch_gap_count,
):
  """Legacy catalog stats docs (stats_kind + *_s fields)."""
  minute_iso = format_minute_iso(minute_bucket)
  failed = int(stats["failed_asins"])

  return {
    "_id": doc_id,
    "stats_kind": "catalog_items",
    "marketplace": marketplace,
    "minute": minute_iso,
    "time": minute_iso,
    "worker": worker_id,
    "total_asins_requested": int(stats["num_asins"]),
    "with_catalog_row_count": int(stats["successful_asins"]),
    "missing_catalog_row_count": failed,
    "missing_catalog_asin_unique_count": failed,
    "task_count": int(task_count),
    "task_duration_s": ms_to_seconds(stats["task_duration_ms"]),
    "spapi_duration_s": ms_to_seconds(stats["spapi_duration_ms"]),
    "api_failed": int(stats["api_failed"]),
    "avg_task_duration_s": ms_to_seconds(
      stats["task_duration_ms"] // task_count if task_count else 0
    ),
    "avg_spapi_duration_s": ms_to_seconds(
      stats["spapi_duration_ms"] // task_count if task_count else 0
    ),
    "avg_spapi_success_s": ms_to_seconds(
      stats["spapi_success_duration_ms"] // spapi_success_count if spapi_success_count else 0
    ),
    "avg_fetch_gap_s": ms_to_seconds(
      stats["fetch_gap_ms"] // fetch_gap_count if fetch_gap_count else 0
    ),
    "fetch_gap_s": ms_to_seconds(stats["fetch_gap_ms"]),
    "fetch_gap_count": int(fetch_gap_count),
    "spapi_success_count": int(spapi_success_count),
  }
