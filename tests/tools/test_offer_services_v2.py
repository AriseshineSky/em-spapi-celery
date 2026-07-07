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
            "B00EKT4MCY": [{"asin": "B00EKT4MCY", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 22.0, "shipping_price": 0.0, "price": 22.0, "shipping_time": {"min": 0, "max": 0, "availability_type": "NOW"}, "rating": {"min": 87.0, "max": 87.0}, "feedback": 2348, "domestic": True, "ships_from": "us", "fba": True, "is_buybox_winner": True, "seller_id": "A3E3FEUB0BHTXD", "is_featured_merchant": True, "prime_information": {"is_prime": True, "is_national_prime": True}, "condition_notes": "", "type": "SpItemOffer"}],
            "B08TVXNKM9": [{"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 18.31, "shipping_price": 0.0, "price": 18.31, "shipping_time": {"min": 0, "max": 0, "availability_type": "NOW"}, "rating": {"min": 91.0, "max": 91.0}, "feedback": 384, "domestic": True, "ships_from": "us", "fba": True, "is_buybox_winner": True, "seller_id": "A2R2RITDJNW1Q6", "is_featured_merchant": True, "prime_information": {"is_prime": True, "is_national_prime": True}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 18.31, "shipping_price": 0.0, "price": 18.31, "shipping_time": {"min": 1, "max": 1, "availability_type": "NOW"}, "rating": {"min": 87.0, "max": 87.0}, "feedback": 8376, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A3W4YSGOME9MU6", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 23.92, "shipping_price": 0.0, "price": 23.92, "shipping_time": {"min": 1, "max": 2, "availability_type": "NOW"}, "rating": {"min": 70.0, "max": 70.0}, "feedback": 3641, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A2VLWSYLFN02RW", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 23.99, "shipping_price": 0.0, "price": 23.99, "shipping_time": {"min": 2, "max": 3, "availability_type": "NOW"}, "rating": {"min": 86.0, "max": 86.0}, "feedback": 679, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A3K3R73C1BSRA6", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 24.37, "shipping_price": 0.0, "price": 24.37, "shipping_time": {"min": 1, "max": 2, "availability_type": "NOW"}, "rating": {"min": 75.0, "max": 75.0}, "feedback": 270030, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A1L4LS2KNDBWYV", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 24.84, "shipping_price": 0.0, "price": 24.84, "shipping_time": {"min": 1, "max": 2, "availability_type": "NOW"}, "rating": {"min": 88.0, "max": 88.0}, "feedback": 177244, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A3SBDOAENTRT1F", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 24.93, "shipping_price": 0.0, "price": 24.93, "shipping_time": {"min": 2, "max": 3, "availability_type": "NOW"}, "rating": {"min": 63.0, "max": 63.0}, "feedback": 1074, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A3GL7UIEGMVRSR", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 24.93, "shipping_price": 0.0, "price": 24.93, "shipping_time": {"min": 2, "max": 3, "availability_type": "NOW"}, "rating": {"min": 57.0, "max": 57.0}, "feedback": 23179, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A3B3RG2J0FKBM3", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 25.33, "shipping_price": 0.0, "price": 25.33, "shipping_time": {"min": 2, "max": 3, "availability_type": "NOW"}, "rating": {"min": 91.0, "max": 91.0}, "feedback": 23880, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A2HG7KNUEK3HVB", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 27.41, "shipping_price": 0.0, "price": 27.41, "shipping_time": {"min": 1, "max": 1, "availability_type": "NOW"}, "rating": {"min": 79.0, "max": 79.0}, "feedback": 18354, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "AKDENCFW3A9SI", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}, {"asin": "B08TVXNKM9", "country": "us", "condition": "new", "subcondition": "new", "currency": "USD", "product_price": 22.99, "shipping_price": 9.53, "price": 32.52, "shipping_time": {"min": 1, "max": 1, "availability_type": "NOW"}, "rating": {"min": 78.0, "max": 78.0}, "feedback": 29859, "domestic": True, "ships_from": "us", "fba": False, "is_buybox_winner": False, "seller_id": "A1NZEJZ10332NK", "is_featured_merchant": True, "prime_information": {"is_prime": False, "is_national_prime": False}, "condition_notes": "", "type": "SpItemOffer"}]
        }

        data = {
            'hits': {
                'hits': [
                    {
                        '_id': asin,
                        '_source': {
                             'asin': asin,
                             'offers': json.dumps(item),
                             'time': datetime.now().replace(microsecond=0).isoformat()
                         }
                    } for asin, item in parsed_response.items()
                ]
            }
        }


        # 调用方法
        offers = self.offer_service.get_lowest_offer(data)

        self.assertIn("B00EKT4MCY", offers)
        self.assertIn("B08TVXNKM9", offers)
        self.assertEqual(offers["B00EKT4MCY"]["price"], 22.0)
        self.assertEqual(offers["B08TVXNKM9"]["price"], 18.31)


if __name__ == "__main__":
    unittest.main()

