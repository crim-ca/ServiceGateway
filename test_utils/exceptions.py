#!/usr/bin/env python2
# coding: utf-8

"""
Testing utilities exception classes.
"""


class ServiceError(Exception):
    """
    Indicates that there was an error with the service use.
    """
    pass


class UnknownService(Exception):
    """
    Indicates that a specified service is of unhandled type.
    """
    pass
