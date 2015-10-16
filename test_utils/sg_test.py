#!/usr/bin/env python
# coding: utf-8

"""
Manual integration test utility for SG.

Sends process request to SG.
"""

from time import sleep
import optparse
import logging
import os

from .manual_test import (annotate_url,
                          status_service,
                          ServiceError,
                          THIS_DIR,
                          S_CONF)


def main():
    """
    Script entry point
    """
    parser = optparse.OptionParser()

    log_conf_fn = os.path.join(THIS_DIR, 'logging.ini')
    parser.add_option("-l",
                      action='store',
                      default=log_conf_fn,
                      dest='logging_conf_fn',
                      help='Set logging configuration filename')

    options = parser.parse_args()[0]

    logging.config.fileConfig(options.logging_conf_fn)
    logger = logging.getLogger(__name__)

    for service_name in S_CONF:
        logger.info("Running tests for service %s", service_name)
        params = {}

        url = S_CONF[service_name]['test_doc']
        if service_name == 'matching':
            txt_url = S_CONF[service_name]['test_txt_doc']
            params['txt_url'] = txt_url
            logger.info("Setting txt_url value at %s", params)

        uuid = annotate_url(service_name, url, params)
        status = None
        while status != "SUCCESS":
            logger.info("Waiting...")
            sleep(5)
            status = status_service(service_name, uuid)
            if status == "FAILURE":
                raise ServiceError(status)

        logger.info("Status : %s", status)


if __name__ == '__main__':
    main()
