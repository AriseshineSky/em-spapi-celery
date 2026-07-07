import os

from dropshipping import logger
import telegram
from telegram.ext import Updater


class TelegramBot:
  _updater = None

  @classmethod
  def _get_updater(cls):
    if cls._updater is not None:
      return cls._updater

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
      return None

    cls._updater = Updater(token=token, use_context=True)
    return cls._updater

  @classmethod
  def send_message(cls, message, chat_id=None, ignore_exc=True):
    updater = cls._get_updater()
    if updater is None:
      return

    chat_id = chat_id or os.getenv('TELEGRAM_DEBUG_GROUP_CHAT_ID')
    if not chat_id:
      return

    try:
      updater.bot.send_message(
        chat_id, message, disable_web_page_preview=True, timeout=10)
    except Exception as e:
      logger.exception(e)
      if not ignore_exc:
        raise
