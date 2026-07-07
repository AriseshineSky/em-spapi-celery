import logging
import os
import sys

ENV = os.getenv("ENV", "prod")
LOG_LEVEL = logging.DEBUG if ENV == "dev" else logging.INFO
logger = logging.getLogger('em_tasks.' + __name__)
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
logger.setLevel(LOG_LEVEL)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
