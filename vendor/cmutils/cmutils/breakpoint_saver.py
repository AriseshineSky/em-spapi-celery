# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import io


class BreakpointSaver(object):
    def __init__(self, bp_path):
        self._bp_path = os.path.abspath(os.path.expanduser(bp_path))

    def save_bp(self, bp):
        """
        Save breakpoint to file.
        bp must be string.
        If could not create breakpoint directory or could not write to breakpoint
        file, exception will be raised.
        """
        bp_dir = os.path.dirname(self._bp_path)
        if not os.path.isdir(bp_dir):
            os.makedirs(bp_dir)

        with io.open(self._bp_path, 'w', encoding='utf-8', errors='ignore') as bp_fh:
            bp_fh.write(bp)

    def get_bp(self):
        """
        Retrieve saved breakpoint from file.
        If bp never saved, return None.
        """
        if os.path.isfile(self._bp_path):
            with io.open(self._bp_path, 'r', encoding='utf-8', errors='ignore') as bp_fh:
                bp = bp_fh.read()
        else:
            bp = None

        return bp

    def clear_bp(self):
        if os.path.isfile(self._bp_path):
            os.remove(self._bp_path)
