# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from pydispatch.robust import sendRobust
# from pydispatch import dispatcher

from dropshipping.signals import mws_unavailable


def mws_wrapper(cls):
    class MwsWrapperClass(cls):
        status = dict()

        def is_active(self, marketplace_id):
            return self.__class__.status.get(self.account_id, {}).get(marketplace_id, True)

        def deactivate(self, marketplace_id, reason=''):
            active = self.is_active(marketplace_id)
            if not active:
                return

            if self.account_id not in self.__class__.status:
                self.__class__.status[self.account_id] = {}

            self.__class__.status[self.account_id][marketplace_id] = False

            # Notify mws api status change
            payload = {
                'seller_id': self.account_id,
                'marketplace': marketplace_id,
                'reason': reason
            }
            return sendRobust(signal=mws_unavailable, sender=self, **payload)
            # return dispatcher.send(signal=mws_unavailable, sender=self, **payload)

    return MwsWrapperClass
