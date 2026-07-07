# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com
import requests
from requests.exceptions import (
    ConnectTimeout,
    ConnectionError,
    ReadTimeout,
    HTTPError,
    RequestException
)
import time
import re
import csv
import io

import six

def is_asin_valid(asin):
    return bool(asin and not asin.isspace() and re.match('[0-9]{10}|[0-9]{9}[0-9X]{1}|[A-Z]{1}[0-9A-Z]{9}', asin))

def pad_asin(asin):
    formatted_asin = asin

    if len(asin) < 10 and not asin.lower().startswith('b'):
        formatted_asin = "{0:0>10}".format(asin)

    return formatted_asin

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


class CsvExporter(object):
    def __init__(
        self, file, include_headers_line=True, join_multivalued=',',
        fields_to_export=None, encoding=None, export_empty_fields=True, **kwargs):
        if not encoding:
            self.encoding = 'utf-8'
        else:
            self.encoding = encoding
        self.include_headers_line = include_headers_line
        self.fields_to_export = fields_to_export
        self.export_empty_fields = export_empty_fields

        self.stream = io.TextIOWrapper(
            file,
            line_buffering=False,
            write_through=True,
            encoding=self.encoding
        ) if six.PY3 else file
        self.csv_writer = csv.writer(self.stream, **kwargs)
        self._headers_not_written = True
        self._join_multivalued = join_multivalued

    def serialize_field(self, field, name, value):
        serializer = field.get('serializer', self._join_if_needed)
        return serializer(value)

    def _join_if_needed(self, value):
        if isinstance(value, (list, tuple)):
            try:
                return self._join_multivalued.join(value)
            except TypeError:  # list in value may not contain strings
                pass
        return value

    def export_item(self, item):
        if self._headers_not_written:
            self._headers_not_written = False
            self._write_headers_and_set_fields_to_export(item)

        fields = self._get_serialized_fields(
            item, default_value='', include_empty=True)
        values = list(self._build_row(x for _, x in fields))
        self.csv_writer.writerow(values)

    def _get_serialized_fields(self, item, default_value=None, include_empty=None):
        """Return the fields to export as an iterable of tuples
        (name, serialized_value)
        """
        if include_empty is None:
            include_empty = self.export_empty_fields

        if self.fields_to_export is None:
            field_iter = six.iterkeys(item)
        else:
            if include_empty:
                field_iter = self.fields_to_export
            else:
                field_iter = (x for x in self.fields_to_export if x in item)

        for field_name in field_iter:
            if field_name in item:
                value = self._join_if_needed(item[field_name])
            else:
                value = default_value

            yield field_name, value

    def _build_row(self, values):
        for s in values:
            try:
                yield to_native_str(s, self.encoding)
            except TypeError:
                yield s

    def _write_headers_and_set_fields_to_export(self, item):
        if self.include_headers_line:
            if not self.fields_to_export:
                self.fields_to_export = list(item.keys())
            row = list(self._build_row(self.fields_to_export))
            self.csv_writer.writerow(row)


def request(method, url=None, **kwargs):

    timeout = kwargs.get('timeout', 60)
    headers = {
        'Accept': 'application/json'
    }
    headers.update(kwargs.get('headers', dict()))

    kwargs['timeout'] = timeout
    kwargs['headers'] = headers

    retries = kwargs.get('max_retries', 3)
    response = None
    while retries > 0:
        retries -= 1
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            break
        except (ConnectTimeout, ConnectionError, ReadTimeout):
            time.sleep(30)
        except HTTPError as err:
            if err.response.status_code < 500:
                raise

            time.sleep(7 if 500 <= err.response.status_code < 600 else 1)
        except RequestException:
            raise

    return response
