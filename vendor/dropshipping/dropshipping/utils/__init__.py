# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com


class ObjectDict(dict):
    """
    Provides '.' access to dictionary keys
    """
    def __init__(self, mapping, *args, **kwargs):
        """
        Create a new mapping. Filters the mapping argument
        to remove any elements that are already methods on the
        object.
        For example, Orders retains its `coupons` method, instead
        of being replaced by the dict describing the coupons endpoint
        """
        filter_args = {k: mapping[k] for k in mapping if k not in dir(self)}
        self.__dict__ = self
        dict.__init__(self, filter_args, *args, **kwargs)

    def __str__(self):
        """
        Display as a normal dict, but filter out underscored items first
        """
        return str({k: self.__dict__[k] for k in self.__dict__ if not k.startswith("_")})

    def __repr__(self):
        return "<%s at %s, %s>" % (type(self).__name__, hex(id(self)), str(self))


from dropshipping.signals import invalid_asin, general_error
from dropshipping.utils.blacklist import create_dog_asin
from pydispatch import dispatcher
from dropshipping.utils.telegram_bot import TelegramBot


dispatcher.connect(create_dog_asin, signal=invalid_asin)
dispatcher.connect(TelegramBot.send_message, signal=general_error)
