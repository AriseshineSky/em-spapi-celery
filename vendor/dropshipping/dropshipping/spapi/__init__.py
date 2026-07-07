
from sp_api.api import (
    Feeds,
    Reports,
    Orders,
    Products,
    Sellers,
    Finances,
    FulfillmentInbound,
    Inventories,
    FulfillmentOutbound,
    CatalogItems,
    CatalogItemsVersion
)


from sp_api import base, util, auth, api
from sp_api.base import *
from sp_api.api.products.products_definitions import GetItemOffersBatchRequest, ItemOffersRequest

from dropshipping.spapi.decorators import spapi_wrapper, get_marketplace
from dropshipping.spapi import monkey_patches
from dropshipping.spapi.monkey_patches import from_marketplace_id
from sp_api.base.marketplaces import Marketplaces


Marketplaces.from_marketplace_id = from_marketplace_id


Feeds = spapi_wrapper(Feeds)
Reports = spapi_wrapper(Reports)
Orders = spapi_wrapper(Orders)
Finances = spapi_wrapper(Finances)
Products = spapi_wrapper(Products)
Sellers = spapi_wrapper(Sellers)
FulfillmentInbound = spapi_wrapper(FulfillmentInbound)
Inventories = spapi_wrapper(Inventories)
FulfillmentOutbound = spapi_wrapper(FulfillmentOutbound)
CatalogItems = spapi_wrapper(CatalogItems)

