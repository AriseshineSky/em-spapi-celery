import unittest
import json
from datetime import datetime
from em_celery import get_offer_service_config, get_amz_offer_filter_config
from em_tasks.utils.offer_services import AmzOfferService

class TestAmzOfferService(unittest.TestCase):
    def setUp(self):
        country = "US"
        filter_cond = get_amz_offer_filter_config(country)
        offer_service_cfg = get_offer_service_config()
        self.offer_service = AmzOfferService(
            offer_service_cfg['host'], offer_service_cfg['port'],
            offer_service_cfg['user'], offer_service_cfg['password'], filter_cond
        )

    def test_get_lowest_offer(self):
        parsed_response = {
            "B0D7QLHBYG": [{"asin": "B0D7QLHBYG", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 5.29, "shipping_price": 0.0, "price": 5.29, "shipping_time": {"min": 0, "max": 0, "availability_type": "NOW"}, "rating": {"min": 97.0, "max": 97.0}, "feedback": 20986, "domestic": True, "ships_from": "us", "fba": True, "is_buybox_winner": True, "seller_id": "A30WUG2ZDGM0XM", "is_featured_merchant": True, "prime_information": {"is_prime": True, "is_national_prime": True}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B0D7QLHBYG", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 5.29, "shipping_price": 1.1, "price": 6.39, "shipping_time": {"min": 4, "max": 5, "availability_type": "NOW"}, "rating": {"min": 97.0, "max": 97.0}, "feedback": 20986, "domestic": False, "ships_from": "hk", "fba": False, "is_buybox_winner": False, "seller_id": "A30WUG2ZDGM0XM", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}
           ],
        }
        data = {
            'hits': {
                'hits': [
                    {
                        '_id': item['asin'],
                        '_source': {
                         'asin': item['asin'],
                         'offers': json.dumps(parsed_response['B0D7QLHBYG']),
                         'time': datetime.now().replace(microsecond=0).isoformat()
                         }
                     } for item in parsed_response['B0D7QLHBYG']]
            }
        }

        # 调用方法
        offers = self.offer_service.get_lowest_offer(data)
        breakpoint()

        self.assertIn("asin1", offers)
        self.assertIn("asin2", offers)
        self.assertEqual(offers["asin1"]["price"], 10)
        self.assertEqual(offers["asin2"]["price"], 20)

        # 确认原始 offers 已存储
        self.assertEqual(self.offer_service.original_offers, parsed_response)


if __name__ == "__main__":
    unittest.main()

