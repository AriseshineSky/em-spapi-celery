# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from distutils.util import strtobool


class ReportRequestListParser(object):
    def parse(self, data):
        d = dict()

        report_request_list_result = data.parsed
        has_next = strtobool(report_request_list_result.get('HasNext', d).get('value', 'false'))
        info = report_request_list_result.get('ReportRequestInfo', d)
        return {
            'has_next': has_next,
            'report_request_info': {
                'report_type': info.get('ReportType', d).get('value', ''),
                'report_processing_status': info.get('ReportProcessingStatus', d).get('value', ''),
                'scheduled': strtobool(info.get('Scheduled', d).get('value', 'false')),
                'report_request_id': info.get('ReportRequestId', d).get('value', ''),
                'started_processing_date': info.get('StartedProcessingDate', d).get('value', ''),
                'submitted_date': info.get('SubmittedDate', d).get('value', ''),
                'start_date': info.get('StartDate', d).get('value', ''),
                'completed_date': info.get('CompletedDate', d).get('value', ''),
                'generated_report_id': info.get('GeneratedReportId', d).get('value', ''),
                'end_date': info.get('EndDate', d).get('value', '')
            }
        }
