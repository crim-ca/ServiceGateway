#!/usr/bin/env python2.7
# coding: utf-8

"""
Simple helper script to load application in development mode.
"""

# -- Standard lib ------------------------------------------------------------
import logging.config
import argparse
import logging
import os

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

# -- Project specific --------------------------------------------------------
from ServiceGateway.__meta__ import __version__


def main():
    """
    Command line entry point.
    """
    log_conf_fn = os.path.join(THIS_DIR, 'ServiceGateway', 'logging.ini')

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-p', '--port', dest='port', type=int, default=5000)
    parser.add_argument("--version", "-v", action="version",
                        version=__version__)
    parser.add_argument('-d', '--debug', dest='debug', action="store_true",
                        default=False)
    parser.add_argument("-l", "--logconf",
                        action='store',
                        default=log_conf_fn,
                        dest='logging_conf_fn',
                        help='Set logging configuration filename')

    args = parser.parse_args()

    # logging.config.fileConfig(opts.logging_conf_fn)
    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.info("Using log configuration file {c}".
                format(c=args.logging_conf_fn))

    from ServiceGateway.rest_api import (configure_home_route, APP)
    # Must be configured also once the settings have been loaded
    configure_home_route()

    APP.run(host='0.0.0.0', port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
