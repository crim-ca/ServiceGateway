#!/usr/bin/env python
# coding:utf-8

"""
Test reactivity of Celery back-end. Loops many times on the creation of an
AsyncResult object creation for a given task id.
"""

import multiprocessing
import logging

from .VestaRestPackage.Service.request_process_mesg import send_task_request
from .VestaRestPackage.Service.request_process_mesg import get_request_info
from .VestaRestPackage.celery_config import APP

POOLWIDTH = 80
POOL = multiprocessing.Pool(POOLWIDTH)


def get_req(uuid):
    """
    Get request information.

    :param uuid: UUID identifying the issued request.
    :returns: Request status / information.
    """
    return get_request_info(uuid, APP)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    LOGGER = logging.getLogger(__name__)
    UPPER_LIMIT = 50
    LOGGER.info(u"Looping {0} times".format(UPPER_LIMIT))

    ITERATION = None
    for ITERATION in range(1, UPPER_LIMIT+1):
        LOGGER.info(u"Requesting new process on backend...")
        REQUEST = send_task_request('http://localhost:8000/short_en.wav',
                                    'diarisation', APP, None, None)
        UUID = REQUEST.task_id

        STATES = POOL.map(get_req, [UUID]*POOLWIDTH)
        LOGGER.info(u"OK: {0}".format(STATES))

    LOGGER.info(u"Looped over query {0} times".format(ITERATION))
