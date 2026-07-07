# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from distutils.util import strtobool


class ReportRequestParser(object):
    def parse(self, data):
        d = dict()

        request_report_result = data.parsed
        info = request_report_result.get('ReportRequestInfo', d)
        return {
            'report_type': info.get('ReportType', d).get('value', ''),
            'status': info.get('ReportProcessingStatus', d).get('value', ''),
            'scheduled': strtobool(info.get('Scheduled', d).get('value', 'false')),
            'report_request_id': info.get('ReportRequestId', d).get('value', ''),
            'submitted_date': info.get('SubmittedDate', d).get('value', ''),
            'start_date': info.get('StartDate', d).get('value', ''),
            'end_date': info.get('EndDate', d).get('value', '')
        }
