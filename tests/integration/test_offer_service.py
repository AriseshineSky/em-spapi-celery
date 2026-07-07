# tests/integration/test_offer_service.py


def test_get_offers_real_request(offer_service):
    marketplace = "ae"
    asins = ["B0DSZV5FD6", "B0D8KPNM3J", "B0FLD68RFQ", "B0FLD671GK", "B06Y5DB6WF"]
    condition = "new"

    offers = offer_service.get_offers(
        marketplace,
        asins,
        condition
    )
    assert isinstance(offers, dict)
    assert set(offers.keys()) == set(asins)

    for asin, offer in offers.items():
        assert offer is None or isinstance(offer, dict)

def test_no_asin_get_offers_real_request(offer_service):
    marketplace = "ae"
    asins = ["B0F87JCB4Y"]
    condition = "new"

    offers = offer_service.get_offers(
        marketplace,
        asins,
        condition
    )
    assert isinstance(offers, dict)
    assert set(offers.keys()) == set(asins)

    for asin, offer in offers.items():
        assert offer is False

