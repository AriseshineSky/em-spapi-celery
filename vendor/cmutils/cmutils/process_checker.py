# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import json
from glob import glob
import shutil
import psutil

def get_subdirectories_name(directory):
    dirs = glob("%s/*/" % directory)
    return [os.path.basename(os.path.dirname(dir_path)) for dir_path in dirs]


class ProcessChecker(object):
    def __init__(self, work_dir):
        self._proc_info_dir = os.path.join(work_dir, 'proc')

    def get_pids(self):
        pids_str = get_subdirectories_name(self._proc_info_dir)
        return [int(pid_str) for pid_str in pids_str]

    def is_running(self, pid):
        running = False

        if not psutil.pid_exists(pid):
            return running

        proc = psutil.Process(pid)

        proc_info_path = self._pid_path(pid)
        if not os.path.isfile(proc_info_path):
            return running

        with open(proc_info_path, 'r') as proc_info_fh:
            try:
                proc_info = json.load(proc_info_fh)
                exist = bool(proc_info['pid'] == pid and proc_info['cmdline'] == proc.cmdline())
                if exist:
                    status = proc.status()
                    running = not bool(
                        status in [psutil.STATUS_STOPPED, psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD])
                else:
                    running = False
            except:
                running = False

        return running

    def is_exist(self, pid):
        return psutil.pid_exists(pid)

    def is_same_task(self, pid1, pid2):
        proc1 = psutil.Process(pid1)
        proc2 = psutil.Process(pid2)
        return proc1.cmdline() == proc2.cmdline()

    def proc_info(self, pid):
        info = dict()

        if not self.is_running(pid):
            return info

        proc_info_path = self._pid_path(pid)
        with open(proc_info_path, 'r') as proc_info_fh:
            try:
                proc_info = json.load(proc_info_fh)
            except:
                proc_info = dict()

        info.update(proc_info)

        return info

    def save_pid(self, pid):
        if not psutil.pid_exists(pid):
            return False

        proc_dir = self._pid_dir(pid)
        proc_info_path = self._pid_path(pid)
        if not os.path.isdir(proc_dir):
            try:
                os.makedirs(proc_dir)
            except:
                return False

        proc = psutil.Process(pid)
        info_dic = dict()
        info_dic['pid'] = proc.pid
        info_dic['create_time'] = proc.create_time()
        info_dic['cmdline'] = proc.cmdline()

        with open(proc_info_path, 'w') as proc_info_fh:
            json.dump(info_dic, proc_info_fh)

        return True

    def remove_pid(self, pid):
        proc_dir = self._pid_dir(pid)
        if not os.path.isdir(proc_dir):
            return False

        try:
            shutil.rmtree(proc_dir)
        except:
            return False

        return True

    def kill_proc(self, pid, force=False):
        if not self.is_running(pid) and not force:
            return False

        try:
            proc = psutil.Process(pid)
            for child_proc in proc.children():
                child_proc.kill()
            proc.kill()
        except psutil.NoSuchProcess:
            return False

        return True

    def _pid_dir(self, pid):
        return os.path.join(self._proc_info_dir, str(pid))

    def _pid_path(self, pid):
        return os.path.join(self._pid_dir(pid), 'info')
