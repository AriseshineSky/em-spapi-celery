# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

__all__ = [
    'InputStreamDisconnected',
    'InvalidSellerID',
    'InvalidAccessKeyId',
    'AccessDenied',
    'InvalidParameterValue',
    'SignatureDoesNotMatch',
    'InvalidAddress',
    'InvalidRequest'
]


class InputStreamDisconnected(Exception):
    pass


class InvalidSellerID(Exception):
    pass


class InvalidAccessKeyId(Exception):
    pass


class AccessDenied(Exception):
    pass


class InvalidParameterValue(Exception):
    pass


class SignatureDoesNotMatch(Exception):
    pass


class InvalidAddress(Exception):
    pass


class InvalidRequest(Exception):
    pass
