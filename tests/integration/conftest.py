import pytest

from em_tasks.utils.offer_services import AmzOfferService
from em_celery import get_amz_offer_filter_config, get_offer_service_config

@pytest.fixture(scope="session")
def offer_service():
    marketplace = "ae"
    filter_cond = get_amz_offer_filter_config(marketplace)
    offer_service_cfg = get_offer_service_config()
    return AmzOfferService(
        offer_service_cfg['host'], offer_service_cfg['port'],
        offer_service_cfg['user'], offer_service_cfg['password'], filter_cond
    )

