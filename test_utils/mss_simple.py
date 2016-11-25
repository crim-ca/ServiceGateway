#!/usr/bin/env python
# coding: utf-8

"""
Manual integration test utility for mss.

Sends test file to MSS, does transcoding, deletes file..
"""

# -- Standard Library --------------------------------------------------------
import optparse
import logging
import os

# -- Project specific --------------------------------------------------------
from .manual_test import (upload_doc,
                          THIS_DIR,
                          get_doc,
                          delete)


def main():
    """
    Script entry point
    """
    parser = optparse.OptionParser(description=__doc__)

    log_conf_fn = os.path.join(THIS_DIR, 'logging.ini')
    base_doc = os.path.join(THIS_DIR, "test_data/1184_103.txt")
    parser.add_option("-l",
                      action='store',
                      default=log_conf_fn,
                      dest='logging_conf_fn',
                      help='Set logging configuration filename')
    parser.add_option("--test_data", action="store", default=base_doc,
                      help="Defaults to {0}".format(base_doc))

    options = parser.parse_args()[0]

    logging.config.fileConfig(options.logging_conf_fn)

    doc_id = upload_doc(options.test_data)
    get_doc(doc_id)

    delete(doc_id)


if __name__ == '__main__':
    main()
