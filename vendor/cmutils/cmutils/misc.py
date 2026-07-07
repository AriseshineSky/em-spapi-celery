# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from importlib import import_module

import six


def to_unicode(text, encoding=None, errors='strict'):
    """Return the unicode representation of a bytes object `text`. If `text`
    is already an unicode object, return it as-is."""
    if isinstance(text, six.text_type):
        return text

    if not isinstance(text, bytes):
        raise TypeError(
            'to_unicode must receive a bytes, str or unicode object, got %s' % type(text).__name__)

    if encoding is None:
        encoding = 'utf-8'

    return text.decode(encoding, errors)

def to_bytes(text, encoding=None, errors='strict'):
    """Return the binary representation of `text`. If `text`
    is already a bytes object, return it as-is."""
    if isinstance(text, bytes):
        return text

    if not isinstance(text, six.string_types):
        raise TypeError(
            'to_bytes must receive a unicode, str or bytes object, got %s' % type(text).__name__)

    if encoding is None:
        encoding = 'utf-8'

    return text.encode(encoding, errors)

def to_native_str(text, encoding=None, errors='strict'):
    """ Return str representation of `text`
    (bytes in Python 2.x and unicode in Python 3.x). """
    if six.PY2:
        return to_bytes(text, encoding, errors)
    else:
        return to_unicode(text, encoding, errors)

def load_object(path):
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ValueError("Error loading object '%s': not a full path" % path)

    module, name = path[:dot], path[dot+1:]
    mod = import_module(module)

    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError("Module '%s' doesn't define any object named '%s'" % (module, name))

    return obj
