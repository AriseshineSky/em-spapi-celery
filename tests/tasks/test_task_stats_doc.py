import datetime
import unittest

from em_tasks.tasks.task_stats_doc import build_catalog_stats_doc, build_offer_stats_doc


class TestTaskStatsDoc(unittest.TestCase):
  def test_build_offer_stats_doc_matches_legacy_schema(self):
    minute = datetime.datetime(2026, 7, 7, 12, 34, tzinfo=datetime.timezone.utc)
    stats = {
      "num_asins": 40,
      "successful_asins": 38,
      "failed_asins": 2,
      "api_failed": 1,
      "task_duration_ms": 13450,
      "spapi_duration_ms": 9000,
      "spapi_success_duration_ms": 8000,
      "fetch_gap_ms": 500,
    }

    doc = build_offer_stats_doc(
      doc_id="offers-uk-offer-worker@mi01eu-pid123_2026-07-07T12:34:00+00:00",
      worker_id="offer-worker@mi01eu",
      marketplace="uk",
      condition="New",
      minute_bucket=minute,
      stats=stats,
      task_count=10,
      spapi_success_count=9,
      fetch_gap_count=5,
    )

    self.assertEqual("item_offers", doc["stats_kind"])
    self.assertEqual("uk", doc["marketplace"])
    self.assertEqual("new", doc["condition"])
    self.assertEqual("offer-worker@mi01eu", doc["worker"])
    self.assertEqual(40, doc["total_asins_requested"])
    self.assertEqual(38, doc["with_offer_row_count"])
    self.assertEqual(2, doc["missing_offer_row_count"])
    self.assertEqual(13.45, doc["task_duration_s"])
    self.assertEqual(9.0, doc["spapi_duration_s"])
    self.assertEqual(0.5, doc["fetch_gap_s"])
    self.assertEqual(1.345, doc["avg_task_duration_s"])

  def test_build_catalog_stats_doc_uses_catalog_row_fields(self):
    minute = datetime.datetime(2026, 7, 7, 12, 34, tzinfo=datetime.timezone.utc)
    stats = {
      "num_asins": 20,
      "successful_asins": 18,
      "failed_asins": 2,
      "api_failed": 0,
      "task_duration_ms": 5000,
      "spapi_duration_ms": 4000,
      "spapi_success_duration_ms": 3500,
      "fetch_gap_ms": 200,
    }

    doc = build_catalog_stats_doc(
      doc_id="catalog-de-catalog-worker@mi01eu-pid456_2026-07-07T12:34:00+00:00",
      worker_id="catalog-worker@mi01eu",
      marketplace="de",
      minute_bucket=minute,
      stats=stats,
      task_count=4,
      spapi_success_count=4,
      fetch_gap_count=2,
    )

    self.assertEqual("catalog_items", doc["stats_kind"])
    self.assertEqual(20, doc["total_asins_requested"])
    self.assertEqual(18, doc["with_catalog_row_count"])
    self.assertEqual(2, doc["missing_catalog_row_count"])
    self.assertNotIn("condition", doc)


if __name__ == "__main__":
  unittest.main()
