# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import time

from dropshipping.mws import COUNTRY_MARKETPLACE_MAPPING
from dropshipping.mws.exceptions import (
    InvalidSellerID,
    InvalidAccessKeyId,
    AccessDenied,
    SignatureDoesNotMatch
)
from dropshipping.spapi.exceptions import SellingApiForbiddenException, SellingApiRequestThrottledException
from dropshipping.utils.report_request_parser import ReportRequestParser
from dropshipping.utils.report_request_list_parser import ReportRequestListParser
from dropshipping.utils.report_list_parser import ReportListParser

from dropshipping import logger

from dropshipping.spapi import ReportType
from dropshipping.spapi import get_marketplace
from dropshipping.spapi import util


class ReportDownloader(object):
    def __init__(self, reports_api):
        self._reports_api = reports_api
        self._report_request_parser = ReportRequestParser()
        self._report_request_list_parser = ReportRequestListParser()
        self._report_list_parser = ReportListParser()

    def download_report(self, report_type, marketplace, start_date=None, end_date=None):
        marketplace = marketplace.lower()
        marketplaceid = COUNTRY_MARKETPLACE_MAPPING.get(marketplace, '')
        if not self._reports_api.is_active(marketplaceid):
            return False

        try:
            response = self._reports_api.request_report(
                report_type, marketplaceids=(marketplaceid),
                start_date=start_date, end_date=end_date)
            report_request_result = self._report_request_parser.parse(response)
            report_request_id = report_request_result.get('report_request_id')
            if not report_request_id:
                return False

            report_id = None
            while True:
                response = self._reports_api.get_report_request_list(requestids=(report_request_id))
                result = self._report_request_list_parser.parse(response)
                status = result['report_request_info']['report_processing_status']
                if status in ['_CANCELLED_', '_DONE_NO_DATA_']:
                    return False

                if status in ('_SUBMITTED_', '_IN_PROGRESS_', '_UNCONFIRMED_'):
                    logger.debug('Report status is %s, waiting for report ready...', status)
                    time.sleep(60)
                    continue

                report_id = result['report_request_info'].get('generated_report_id', None)
                break

            if not report_id:
                return False

            report = self._reports_api.get_report(report_id)
            return report.parsed if report.parsed else report.response.content
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            self._reports_api.deactivate(marketplaceid, str(e))
            return False

    def download_generated_report(
            self, requestids=(), max_count=None, types=(), acknowledged=None,
            fromdate=None, todate=None, next_token=None, acknowledge_after_download=True):
        try:
            response = self._reports_api.get_report_list(
                requestids=requestids, max_count=max_count, types=types,
                acknowledged=acknowledged, fromdate=fromdate, todate=todate,
                next_token=next_token)
            report_list_result = self._report_list_parser.parse(response)
            if 'report_infos' not in report_list_result or not report_list_result['report_infos']:
                return False

            for report_info in report_list_result['report_infos']:
                time.sleep(60)
                report = self._reports_api.get_report(report_info['report_id'])
                report_info['content'] = report.parsed if report.parsed else report.response.content

                yield report_info

            report_ids = [
                report_info['report_id'] for report_info in report_list_result['report_infos']]
            if acknowledge_after_download and report_ids:
                self._reports_api.update_report_acknowledgements(report_ids, 'true')
        except (InvalidSellerID, InvalidAccessKeyId, AccessDenied, SignatureDoesNotMatch) as e:
            logger.exception(e)
            return False

        return True


class SpReportDownloader:
    def __init__(self, reports_api):
        self._reports_api = reports_api

    def download_report(self, report_type: ReportType, marketplace: str,
                        start_date=None, end_date=None, file=None, character_code: str = 'iso-8859-1', **kwargs):
        marketplace = get_marketplace(marketplace)
        marketplaceid = marketplace.marketplace_id
        if not self._reports_api.is_active(marketplace.marketplace_id):
            return False

        try:
            response = None
            tried = 1
            while tried <= 10:
                try:
                    response = self._reports_api.create_report(
                        reportType=report_type, marketplaceIds=[marketplaceid],
                        dataStartTime=start_date, dataEndTime=end_date, **kwargs)
                    break
                except SellingApiRequestThrottledException:
                    logger.info('Throttled when downloading report, wait for 20 seconds in the %s time...', tried)
                    time.sleep(20)
                    tried += 1

            report_id = response.payload.get('reportId')
            if not report_id:
                return False
            return self.download_report_by_report_id(report_id, file, character_code)
        except SellingApiForbiddenException as e:
            logger.exception(e)
            self._reports_api.deactivate(marketplaceid, str(e))
            return False

    @util.throttle_retry(tries=8, delay=10, rate=1.2)
    def download_report_by_report_id(self, report_id, file=None, character_code: str = 'iso-8859-1'):
        report_document_id = None
        while True:
            response = self._reports_api.get_report(report_id)
            result = response.payload
            status = result['processingStatus']
            if status in ['CANCELLED', 'FATAL']:
                return False

            if status in ('IN_QUEUE', 'IN_PROGRESS'):
                logger.debug('Report status is %s, waiting for report ready...', status)
                time.sleep(30)
                continue

            report_document_id = result.get('reportDocumentId', None)
            break

        if not report_document_id:
            return False

        res = self._reports_api.get_report_document(report_document_id, download=True, file=file,
                                                    character_code=character_code)
        return res.payload.get('document')

    def download_inventory_report(self, marketplace, **kwargs):
        return self.download_report(ReportType.GET_FLAT_FILE_OPEN_LISTINGS_DATA, marketplace, **kwargs)

    def download_inactive_listing_report(self, marketplace, **kwargs):
        return self.download_report(ReportType.GET_MERCHANT_LISTINGS_INACTIVE_DATA, marketplace, **kwargs)

    def download_active_listing_report(self, marketplace, **kwargs):
        return self.download_report(ReportType.GET_MERCHANT_LISTINGS_DATA, marketplace, **kwargs)

    def download_all_listing_report(self, marketplace, **kwargs):
        return self.download_report(ReportType.GET_MERCHANT_LISTINGS_ALL_DATA, marketplace, **kwargs)

    def download_seller_feedback_report(self, marketplace, start_date, end_date=None, **kwargs):
        return self.download_report(ReportType.GET_SELLER_FEEDBACK_DATA, marketplace, start_date=start_date,
                                    end_date=end_date, **kwargs)

    def download_seller_performance_report(self, marketplace, start_date, end_date=None, **kwargs):
        return self.download_report(ReportType.GET_V1_SELLER_PERFORMANCE_REPORT, marketplace, start_date=start_date,
                                    end_date=end_date, **kwargs)

    @util.throttle_retry(tries=8, delay=10, rate=1.2)
    def get_reports(self, report_types=None, marketplace: str=None, created_since=None, created_until=None,
                    processing_statuses=None, page_size=10, next_token=None):
        if next_token is not None:
            response = self._reports_api.get_reports(nextToken=next_token)
        else:
            if processing_statuses is None:
                processing_statuses = ['DONE']
            marketplace = get_marketplace(marketplace)
            marketplaceid = marketplace.marketplace_id

            response = self._reports_api.get_reports(
                reportTypes=report_types,
                processingStatuses=processing_statuses,
                marketplaceIds=[marketplaceid],
                pageSize=page_size,
                createdSince=created_since,
                createdUntil=created_until,
            )
        return response

    def download_generated_report(self, report_types, marketplace: str, created_since, created_until,
                                  processing_statuses=None, page_size=10
                                  ):
        try:
            response = self.get_reports(
                report_types=report_types,
                marketplace=marketplace,
                created_since=created_since,
                created_until=created_until,
                processing_statuses=processing_statuses,
                page_size=page_size
            )
            report_list_result = response.payload.get('reports', [])
            for report_info in report_list_result:
                time.sleep(6)
                report_id = report_info['reportId']
                yield self.download_report_by_report_id(report_id)

            next_token = response.payload.get('nextToken')
            while next_token is not None:
                response = self.get_reports(next_token=next_token)
                for report_info in response.payload.get('reports', []):
                    time.sleep(5)
                    report_id = report_info['reportId']
                    yield self.download_report_by_report_id(report_id)
                next_token = response.payload.get('nextToken')
        except SellingApiForbiddenException as e:
            logger.exception(e)
            self._reports_api.deactivate(get_marketplace(marketplace).marketplace_id, str(e))
            return False

        return True
