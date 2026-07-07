# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from datetime import datetime
import os


class HeartBeater(object):
    def __init__(self, path, expire=15):
        self._path = path
        self._format = '%Y-%m-%dT%H:%M:%S'
        self._expire = expire

    def beat(self):
        with open(self._path, 'w') as heartbeat_fd:
            heartbeat_fd.write(datetime.now().strftime(self._format))
            heartbeat_fd.flush()

    def is_alive(self):
        if not os.path.isfile(self._path):
            return False

        alive = True
        with open(self._path, 'r') as heartbeat_fd:
            last_update_time_str = heartbeat_fd.read()
            try:
                last_update_time = datetime.strptime(
                    last_update_time_str, self._format)
                not_update_time = datetime.now() - last_update_time
                if not_update_time.total_seconds() > self._expire * 60:
                    alive = False
            except ValueError:
                alive = False

        return alive

    def stop(self):
        if os.path.isfile(self._path):
            try:
                os.remove(self._path)
            except:
                pass
