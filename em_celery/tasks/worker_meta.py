# -*- coding: utf-8 -*-

import os


def build_worker_meta(request):
  node, host = request.hostname.split("@", 1)
  return {
    "worker_id": f"{node}@{host}",
    "node": node,
    "host": host,
    "pid": os.getpid(),
  }
