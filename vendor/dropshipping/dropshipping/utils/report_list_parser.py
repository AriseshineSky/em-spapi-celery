# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from distutils.util import strtobool


class ReportListParser(object):
    def parse(self, data):
        d = dict()

        report_list_result = data.parsed
        has_next = strtobool(report_list_result.get('HasNext', d).get('value', 'false'))
        info_list = report_list_result.get('ReportInfo', [])
        if not isinstance(info_list, list):
            info_list = [info_list]

        report_infos = []
        for info in info_list:
            report_infos.append({
                'report_type': info.get('ReportType', d).get('value', ''),
                'acknowledged': strtobool(info.get('Acknowledged', d).get('value', 'false')),
                'report_id': info.get('ReportId', d).get('value', ''),
                'available_date': info.get('AvailableDate', d).get('value', ''),
                'report_request_id': info.get('ReportRequestId', d).get('value', '')
            })

        return {
            'has_next': has_next,
            'report_infos': report_infos
        }
