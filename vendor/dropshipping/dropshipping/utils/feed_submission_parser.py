# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from distutils.util import strtobool


class FeedSubmissionParser(object):
    def parse(self, data):
        d = dict()

        feed_submission_info = data.parsed
        info = feed_submission_info.get('FeedSubmissionInfo', d)
        return {
            'feed_submission_id': info.get('FeedSubmissionId', d).get('value', ''),
            'feed_type': info.get('FeedType', d).get('value', ''),
            'status': info.get('FeedProcessingStatus', d).get('value', ''),
            'submitted_date': info.get('SubmittedDate', d).get('value', '')
        }
