from dropshipping import logger
from dropshipping.spapi import Marketplaces, get_marketplace
import time
from dropshipping.spapi.exceptions import SellingApiForbiddenException


def str_to_file_like_object(s):
    class FileLike:
        def __init__(self, s):
            self.s = s

        def read(self):
            return self.s

        def write(self):
            pass

    return FileLike(s)


class FeedUploader:
    def __init__(self, feeds_api):
        self.feeds_api = feeds_api

    def submit_feed(self, feed_type, feeds, content_type='text/tsv', check_res=True, **kwargs):
        """
        Args:
            feed_type: https://developer-docs.amazon.com/sp-api/docs/feed-type-values
            feeds: File or str. if str, will make it a file like object
            content_type: str
            check_res: bool

        Returns:
            if check_res:
                submission result document
            else:
                None
        """

        if not hasattr(feeds, 'read'):
            feeds_file = str_to_file_like_object(feeds)
        else:
            feeds_file = feeds

        if 'marketplace' not in kwargs:
            raise ValueError('Missing required argument: marketplace')

        marketplace = get_marketplace(kwargs.pop('marketplace'))
        marketplace_id = marketplace.marketplace_id
        kwargs['marketplaceIds'] = [marketplace_id]

        try:
            _, res = self.feeds_api.submit_feed(feed_type, feeds_file, content_type, **kwargs)
            if not check_res:
                return True
            # check response
            feed_id = res.payload.get('feedId')
            if feed_id is None:
                logger.info('Could not get feed_id, please check it...')
                return False
            result_feed_document_id = None
            while True:
                result = self.feeds_api.get_feed(feed_id).payload
                status = result['processingStatus']
                if status in ['CANCELLED', 'FATAL']:
                    logger.debug('Submission processing error. Quit.')
                    return False

                if status in ('IN_QUEUE', 'IN_PROGRESS'):
                    logger.debug('Submit feed status is %s, waiting for submission ready...', status)
                    time.sleep(60)
                    continue

                result_feed_document_id = result.get('resultFeedDocumentId')
                break
            if result_feed_document_id is None:
                logger.info('Could not get result_feed_document_id, please check it...')
                return False
            result_document = self.feeds_api.get_feed_result_document(result_feed_document_id)
            # logger.info('Submit feed status is DONE, result:\n-------------------\n%s', result_document)
            return result_document
        except SellingApiForbiddenException as e:
            logger.exception(e)
            self.feeds_api.deactivate(marketplace_id, str(e))
            return False

    def submit_price_feed(self, marketplace, feeds, check_res=False, **kwargs):
        feed_type = 'POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA'
        return self.submit_feed(feed_type, feeds, check_res=check_res, marketplace=marketplace, **kwargs)

    def submit_inventory_feed(self, marketplace, feeds, check_res=True, **kwargs):
        feed_type = "POST_FLAT_FILE_INVLOADER_DATA"
        return self.submit_feed(feed_type, feeds, check_res=check_res, marketplace=marketplace, **kwargs)

    def submit_refund_feed(self, marketplace, feeds, check_res=True, **kwargs):
        feed_type = 'POST_FLAT_FILE_PAYMENT_ADJUSTMENT_DATA'
        return self.submit_feed(feed_type, feeds, check_res=check_res, marketplace=marketplace, **kwargs)

    def submit_cancellation_feed(self, marketplace, feeds, check_res=True, **kwargs):
        feed_type = 'POST_FLAT_FILE_ORDER_ACKNOWLEDGEMENT_DATA'
        return self.submit_feed(feed_type, feeds, check_res=check_res, marketplace=marketplace, **kwargs)

    def submit_fulfillment_feed(self, marketplace, feeds, check_res=True, **kwargs):
        feed_type = 'POST_FLAT_FILE_FULFILLMENT_DATA'
        return self.submit_feed(feed_type, feeds, check_res=check_res, marketplace=marketplace, **kwargs)

    def submit_tracking_feed(self, marketplace, feeds, check_res=True, **kwargs):
        return self.submit_fulfillment_feed(feeds, marketplace, check_res=check_res, **kwargs)

    def submit_invoice(self, marketplace, feeds, check_res=True, **kwargs):
        feed_type = 'UPLOAD_VAT_INVOICE'
        return self.submit_feed(feed_type, feeds, check_res=check_res, marketplace=marketplace, **kwargs)





