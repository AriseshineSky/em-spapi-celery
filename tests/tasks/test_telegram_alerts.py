# -*- coding: utf-8 -*-
"""Telegram alerts from Celery task exception handlers.

Which exceptions send Telegram (production paths):

| Task | Exception | Telegram? | Message prefix |
|------|-----------|-----------|----------------|
| offer | SellingApiForbiddenException | yes | [SellingApiForbidden] |
| offer | AuthorizationError | yes | [SellingApiForbidden] |
| offer | exceptions_to_retry (throttle/5xx/…) | only after >250 rejects | [SpapiItemOffersRejectedReset] |
| offer | exceptions_not_retry / other | no | — |
| catalog | SellingApiForbiddenException | yes | [SellingApiForbidden] |
| catalog | exceptions_to_retry | no | — |
| catalog | exceptions_not_retry / other | no | — |

CLI `telegram_test_send` is a manual probe (same bot/chat config), not an exception path.
"""

from __future__ import annotations

import unittest
from unittest import mock

from celery.exceptions import Ignore, Reject
from click.testing import CliRunner
from sp_api.base.exceptions import (
  SellingApiForbiddenException,
  SellingApiNotFoundException,
  SellingApiRequestThrottledException,
  SellingApiServerException,
)

from em_celery.tasks.spapi_update_catalog_items_task import spapi_update_catalog_items
from em_celery.tasks.spapi_update_item_offers_task import spapi_update_item_offers
from em_celery.tools.telegram_test_send import telegram_test_send

# Import after em_celery tasks (avoids sp_api.auth circular import at collection time)
from sp_api.auth.exceptions import AuthorizationError


def _api_error(message='err', code='Error'):
  return [{'message': message, 'code': code}]


def _task_self(*, hostname='offer-worker@testhost', rejected=0):
  self = mock.MagicMock()
  self.spapi = mock.MagicMock()
  self.offer_service = mock.MagicMock()
  self.product_service = mock.MagicMock()
  self.bot = mock.MagicMock()
  self.group_chat_id = '-100123456'
  self.request.hostname = hostname
  self.rejected_tasks_cnt = rejected
  return self


def _run_offer(self, *args, **kwargs):
  fn = spapi_update_item_offers._get_current_object().run.__func__
  return fn(self, *args, **kwargs)


def _run_catalog(self, *args, **kwargs):
  fn = spapi_update_catalog_items._get_current_object().run.__func__
  return fn(self, *args, **kwargs)


class TestOfferTelegramAlerts(unittest.TestCase):
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.app.control.broadcast')
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.SpapiUpdateItemOffersTask')
  def test_forbidden_sends_telegram_and_shutdown(self, MockBiz, mock_broadcast, _meta):
    MockBiz.return_value.run.side_effect = SellingApiForbiddenException(
      _api_error('forbidden', 'Unauthorized'), None)
    self_ = _task_self()

    with self.assertRaises(Reject):
      _run_offer(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_called_once_with(
      '-100123456',
      '[SellingApiForbidden] Host: offer-worker@testhost, API: GetItemOffersBatch\n',
    )
    mock_broadcast.assert_called_once_with(
      'shutdown', destination=['offer-worker@testhost'])

  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.app.control.broadcast')
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.SpapiUpdateItemOffersTask')
  def test_authorization_error_sends_telegram_and_shutdown(self, MockBiz, mock_broadcast, _meta):
    MockBiz.return_value.run.side_effect = AuthorizationError(401, 'bad token', 401)
    self_ = _task_self()

    with self.assertRaises(Reject):
      _run_offer(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_called_once()
    self.assertIn('[SellingApiForbidden]', self_.bot.send_message.call_args[0][1])
    mock_broadcast.assert_called_once()

  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.SpapiUpdateItemOffersTask')
  def test_retryable_under_threshold_no_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = SellingApiRequestThrottledException(
      _api_error('throttled', 'QuotaExceeded'), None)
    self_ = _task_self(rejected=10)

    with self.assertRaises(Reject):
      _run_offer(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_not_called()
    self.assertEqual(11, self_.rejected_tasks_cnt)

  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.SpapiUpdateItemOffersTask')
  def test_retryable_over_threshold_sends_reset_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = SellingApiServerException(
      _api_error('server', 'InternalError'), None)
    self_ = _task_self(rejected=250)

    with self.assertRaises(Reject):
      _run_offer(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_called_once()
    msg = self_.bot.send_message.call_args[0][1]
    self.assertIn('[SpapiItemOffersRejectedReset]', msg)
    self.assertIn('offer-worker@testhost', msg)
    self.assertEqual(0, self_.rejected_tasks_cnt)

  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.SpapiUpdateItemOffersTask')
  def test_not_retry_no_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = SellingApiNotFoundException(
      _api_error('missing', 'NotFound'), None)
    self_ = _task_self()

    with self.assertRaises(Ignore):
      _run_offer(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_not_called()

  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_item_offers_task.SpapiUpdateItemOffersTask')
  def test_generic_exception_no_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = RuntimeError('boom')
    self_ = _task_self()

    with self.assertRaises(Ignore):
      _run_offer(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_not_called()


class TestCatalogTelegramAlerts(unittest.TestCase):
  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.app.control.broadcast')
  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.SpapiUpdateCatalogItemsTask')
  def test_forbidden_sends_telegram_and_shutdown(self, MockBiz, mock_broadcast, _meta):
    MockBiz.return_value.run.side_effect = SellingApiForbiddenException(
      _api_error('forbidden', 'Unauthorized'), None)
    self_ = _task_self(hostname='catalog-worker@testhost')

    with self.assertRaises(Reject):
      _run_catalog(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_called_once()
    msg = self_.bot.send_message.call_args[0][1]
    self.assertIn('[SellingApiForbidden]', msg)
    self.assertIn('GetCatalogItems', msg)
    self.assertIn('catalog-worker@testhost', msg)
    mock_broadcast.assert_called_once_with(
      'shutdown', destination=['catalog-worker@testhost'])

  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.SpapiUpdateCatalogItemsTask')
  def test_retryable_no_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = SellingApiRequestThrottledException(
      _api_error('throttled', 'QuotaExceeded'), None)
    self_ = _task_self(hostname='catalog-worker@testhost')

    with self.assertRaises(Reject):
      _run_catalog(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_not_called()

  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.SpapiUpdateCatalogItemsTask')
  def test_not_retry_no_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = SellingApiNotFoundException(
      _api_error('missing', 'NotFound'), None)
    self_ = _task_self(hostname='catalog-worker@testhost')

    with self.assertRaises(Ignore):
      _run_catalog(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_not_called()

  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.build_worker_meta', return_value={})
  @mock.patch('em_celery.tasks.spapi_update_catalog_items_task.SpapiUpdateCatalogItemsTask')
  def test_generic_exception_no_telegram(self, MockBiz, _meta):
    MockBiz.return_value.run.side_effect = RuntimeError('boom')
    self_ = _task_self(hostname='catalog-worker@testhost')

    with self.assertRaises(Ignore):
      _run_catalog(self_, 'us', ['B0TESTASIN01'])

    self_.bot.send_message.assert_not_called()


class TestTelegramTestSendCli(unittest.TestCase):
  def test_sends_when_configured(self):
    bot = mock.MagicMock()
    runner = CliRunner()
    with mock.patch('em_celery.tools.telegram_test_send.get_bot', return_value=bot), \
         mock.patch('em_celery.tools.telegram_test_send.get_group_chat_id', return_value='-1001'), \
         mock.patch('em_celery.tools.telegram_test_send.socket.gethostname', return_value='testhost'):
      result = runner.invoke(telegram_test_send, [])

    self.assertEqual(0, result.exit_code, result.output)
    bot.send_message.assert_called_once()
    args = bot.send_message.call_args[0]
    self.assertEqual('-1001', args[0])
    self.assertIn('[TelegramTest]', args[1])
    self.assertIn('testhost', args[1])

  def test_custom_message(self):
    bot = mock.MagicMock()
    runner = CliRunner()
    with mock.patch('em_celery.tools.telegram_test_send.get_bot', return_value=bot), \
         mock.patch('em_celery.tools.telegram_test_send.get_group_chat_id', return_value='-1001'):
      result = runner.invoke(telegram_test_send, ['-m', 'hello-alert'])

    self.assertEqual(0, result.exit_code, result.output)
    self.assertEqual('hello-alert', bot.send_message.call_args[0][1])

  def test_missing_bot_exits_nonzero(self):
    runner = CliRunner()
    with mock.patch('em_celery.tools.telegram_test_send.get_bot', return_value=None), \
         mock.patch('em_celery.tools.telegram_test_send.get_group_chat_id', return_value='-1001'):
      result = runner.invoke(telegram_test_send, [])

    self.assertEqual(1, result.exit_code)
    self.assertIn('api_token', result.output)

  def test_missing_chat_id_exits_nonzero(self):
    runner = CliRunner()
    with mock.patch('em_celery.tools.telegram_test_send.get_bot', return_value=mock.MagicMock()), \
         mock.patch('em_celery.tools.telegram_test_send.get_group_chat_id', return_value=''):
      result = runner.invoke(telegram_test_send, [])

    self.assertEqual(1, result.exit_code)
    self.assertIn('group_chat_id', result.output)

  def test_send_failure_exits_nonzero(self):
    bot = mock.MagicMock()
    bot.send_message.side_effect = RuntimeError('network')
    runner = CliRunner()
    with mock.patch('em_celery.tools.telegram_test_send.get_bot', return_value=bot), \
         mock.patch('em_celery.tools.telegram_test_send.get_group_chat_id', return_value='-1001'):
      result = runner.invoke(telegram_test_send, [])

    self.assertEqual(1, result.exit_code)
    self.assertIn('send failed', result.output)


if __name__ == '__main__':
  unittest.main()
