# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from __future__ import absolute_import

import time

from dropshipping.mws import MWS_ERROR_CODES
from dropshipping.utils.misc import load_object

from mws import mws
from mws import utils
from wrapt import patch_function_wrapper

def parse_mws_error(e):
    code = None
    message = ''
    try:
        parsed_response = mws.DictWrapper(e.response.text, 'Error').parsed

        code = parsed_response.get('Code', dict()).get('value', None)
        message = parsed_response.get('Message', dict()).get('value', '')
    except:
        pass

    return (code, message)

@patch_function_wrapper(mws.MWS, 'make_request')
def make_request(wrapped, instance, args, kwargs):
    codes_critical = ['AccessDenied', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']
    codes_to_retry = ['InternalError', 'QuotaExceeded', 'RequestThrottled']
    codes_not_retry = [
        'InputStreamDisconnected', 'InvalidParameterValue', 'InvalidAddress',
        'InvalidRequest'
    ]

    val = None
    num_retries = 12
    max_retry = num_retries

    while num_retries > 0:
        try:
            val = wrapped(*args, **kwargs)
            break
        except mws.MWSError as e:
            code, message = parse_mws_error(e)
            if code is None or code not in MWS_ERROR_CODES:
                try:
                    code = int(code)
                    if code >= 500:
                        num_retries -= 1
                        time.sleep(max_retry - num_retries)
                        continue
                except ValueError:
                    pass

                raise e

            if code in codes_to_retry:
                num_retries -= 1
                time.sleep(max_retry - num_retries)
                continue
            elif code == 'InvalidParameterValue' and \
                message.find('Invalid seller id') != -1:
                classobj = load_object('dropshipping.mws.exceptions.InvalidSellerID')
                raise classobj(message)
            elif code in codes_critical:
                classobj = load_object('dropshipping.mws.exceptions.{}'.format(code))
                raise classobj(message)
            elif code in codes_not_retry:
                break
            else:
                raise e

    return val

def update_report_acknowledgements(self, report_ids=(), acknowledged='true'):
    data = dict(Action='UpdateReportAcknowledgements',
                Acknowledged=acknowledged)
    data.update(utils.enumerate_param('ReportIdList.Id.', report_ids))
    return self.make_request(data)
