# -*- coding: utf-8 -*-
"""Missing ASINs go to the single ``amz_products_missing`` index only.

The legacy per-market ``amz_products_missing_{mp}`` indices are deprecated: their
history was backfilled into the unified index (em-listing ``amz-merge-missing``)
and every reader goes through ``delivery/missing_index.py::known_missing()``.
"""

import unittest

from em_tasks.tasks.spapi_update_catalog_items_task import (
  UNIFIED_MISSING_INDEX,
  SpapiUpdateCatalogItemsTask,
)


class FakeProductService():
  def __init__(self, failing_indexes=()):
    self.saved = []
    self.ensured = []
    self.failing_indexes = set(failing_indexes)

  def ensure_indice(self, indice_name, settings=None):
    self.ensured.append((indice_name, settings))
    return True

  def save_products(self, indice_name, products):
    if indice_name in self.failing_indexes:
      raise RuntimeError("es down")
    self.saved.append((indice_name, [dict(p) for p in products]))


def build_task(product_service, marketplace="jp"):
  worker = {"worker_id": "catalog-worker@test", "pid": 1234}
  return SpapiUpdateCatalogItemsTask(
    None, product_service, marketplace, ["B0AAA11111"], worker=worker
  )


class MissingAsinsWriteTest(unittest.TestCase):

  def setUp(self):
    SpapiUpdateCatalogItemsTask.task_stats.clear()
    SpapiUpdateCatalogItemsTask.minute_bucket = None
    SpapiUpdateCatalogItemsTask._last_task_finish_ts = None

  def test_only_the_unified_index_is_written(self):
    ps = FakeProductService()
    build_task(ps).save_missing_asins(["B0AAA11111"], "2026-01-01T00:00:00")

    self.assertEqual([UNIFIED_MISSING_INDEX], [row[0] for row in ps.saved])
    index_name, docs = ps.saved[0]
    self.assertEqual(
      [{
        "_id": "jp:B0AAA11111",
        "asin": "B0AAA11111",
        "marketplace": "jp",
        "time": "2026-01-01T00:00:00",
      }],
      docs,
    )

  def test_index_is_created_once_with_unified_mappings(self):
    ps = FakeProductService()
    task = build_task(ps)
    task.save_missing_asins(["B0AAA11111"], "2026-01-01T00:00:00")
    task.save_missing_asins(["B0BBB22222"], "2026-01-01T00:00:01")

    self.assertEqual(1, len(ps.ensured))
    index_name, settings = ps.ensured[0]
    self.assertEqual(UNIFIED_MISSING_INDEX, index_name)
    self.assertEqual(
      {"asin", "marketplace", "time"},
      set(settings["mappings"]["properties"]),
    )

  def test_empty_input_writes_nothing(self):
    ps = FakeProductService()
    build_task(ps).save_missing_asins([], "2026-01-01T00:00:00")

    self.assertEqual([], ps.saved)
    self.assertEqual([], ps.ensured)

  def test_write_failure_is_logged_not_raised(self):
    ps = FakeProductService(failing_indexes={UNIFIED_MISSING_INDEX})
    build_task(ps).save_missing_asins(["B0AAA11111"], "2026-01-01T00:00:00")

    self.assertEqual([], ps.saved)


if __name__ == "__main__":
  unittest.main()