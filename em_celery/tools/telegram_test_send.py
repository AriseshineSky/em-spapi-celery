# -*- coding: utf-8 -*-
"""Send a Telegram test message using the same config path as Celery workers."""

import socket
import sys

import click

from em_celery import get_bot, get_group_chat_id


@click.command()
@click.option(
  '-m', '--message',
  default=None,
  help='Message body (default: hostname + TelegramTest).',
)
def telegram_test_send(message):
  """Verify production Telegram alerts (same bot/chat as Forbidden handlers)."""
  bot = get_bot()
  chat_id = get_group_chat_id()

  if bot is None:
    click.echo(
      'ERROR: Telegram bot not configured. '
      'Set [telegram] api_token in ~/.em_celery/config.ini '
      'or TELEGRAM_BOT_TOKEN.',
      err=True,
    )
    sys.exit(1)

  if not chat_id:
    click.echo(
      'ERROR: group_chat_id empty. '
      'Set [telegram] group_chat_id in ~/.em_celery/config.ini '
      'or TELEGRAM_GROUP_CHAT_ID.',
      err=True,
    )
    sys.exit(1)

  host = socket.gethostname()
  text = message or f'[TelegramTest] host={host} ok'
  try:
    bot.send_message(chat_id, text)
  except Exception as e:
    click.echo(f'ERROR: send failed: {e}', err=True)
    sys.exit(1)

  click.echo(f'sent ok chat_id={chat_id} host={host}')
  click.echo(f'message: {text}')


if __name__ == '__main__':
  telegram_test_send()
