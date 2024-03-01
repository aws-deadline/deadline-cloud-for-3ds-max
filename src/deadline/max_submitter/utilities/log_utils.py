# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Global logger for 3ds Max Submitter
"""

import logging
from logging.handlers import RotatingFileHandler
import os

LOGGING_FORMAT_FILE = (
    "%(asctime)s %(levelname)8s {%(threadName)-10s}:  %(module)s %(funcName)s: %(message)s"
)
LOGGING_FORMAT_COUT = (
    "[%(name)s] %(levelname)8s:  (%(threadName)-10s)  %(module)s %(funcName)s: %(message)s"
)
LOG_DIRECTORY = "~/.deadline/logs/submitters/"
LOG_NAME = "3dsmax.log"
DATE_FORMAT = "%y%m%dZ%H%M%S"


def configure_logging():
    """
    Configures stream and file handlers for the root logger.
    Logs get added to the users .deadline/logs/3dsmax directory.
    """
    logger = logging.root
    if logger.hasHandlers():
        logger.warning("Logger already has handlers")
        return

    cout = logging.StreamHandler()

    dir_ = os.path.expanduser(LOG_DIRECTORY)
    file = dir_ + LOG_NAME
    # create path and/or dir if it doesn't exist yet
    if not os.path.exists(file):
        if not os.path.exists(dir_):
            os.makedirs(dir_)
        open(file, "w+")
    fh = RotatingFileHandler(file, maxBytes=10485760, backupCount=5)

    formatter = logging.Formatter(fmt=LOGGING_FORMAT_COUT, datefmt=DATE_FORMAT)
    formatter_file = logging.Formatter(fmt=LOGGING_FORMAT_FILE)
    cout.setFormatter(formatter)
    fh.setFormatter(formatter_file)
    logger.addHandler(cout)
    logger.addHandler(fh)
