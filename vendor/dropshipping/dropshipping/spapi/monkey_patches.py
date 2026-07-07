from wrapt import patch_function_wrapper
from sp_api.base.client import Client
from sp_api.base.marketplaces import Marketplaces
from sp_api.api import Reports
from sp_api.base import sp_endpoint, fill_query_params
import requests
import zlib


from dropshipping.spapi.exceptions import (
    SellingApiBadRequestException,
    SellingApiInvalidAsinException
)


@patch_function_wrapper(Client, '_request')
def _request(wrapped, instance, args, kwargs):
    try:
        return wrapped(*args, **kwargs)
    except SellingApiBadRequestException as e:
        if 'invalid ASIN' in e.message:
            raise SellingApiInvalidAsinException(e.error, e.headers)


def from_marketplace_id(marketplace_id):
    for marketplace in Marketplaces:
        if marketplace.marketplace_id == marketplace_id:
            return marketplace
    return None


# @patch_function_wrapper(Reports, 'get_report_document')
# @sp_endpoint('/reports/2021-06-30/documents/{}', method='GET')
# def get_report_document(wrapped, instance, args, kwargs):
#     res = instance._request(fill_query_params(kwargs.pop('path'), args[0]), add_marketplace=False)
#     if kwargs['download'] or kwargs['file'] or ('decrypt' in kwargs and kwargs['decrypt']):
#         document = requests.get(res.payload.get('url')).content
#         if 'compressionAlgorithm' in res.payload:
#             document = zlib.decompress(bytearray(document), 15 + 32)
#         document = document.decode(kwargs['character_code'])
#         if kwargs['download']:
#             res.payload.update({
#                 'document': document
#             })
#         if kwargs['file']:
#             instance._handle_file(kwargs['file'], document, kwargs['character_code'])
#     return res

