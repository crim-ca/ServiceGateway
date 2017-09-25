#!/usr/bin/env python
# coding: utf-8

"""
Various exception classes used by the service gateway and utilities.
"""


class RubberException(Exception):
    """
    Base exception class for elasticity functions.
    """
    pass


class InsufficientResources(RubberException):
    """
    Indicates that no more room for other Virtual machine instances in given
    cloud
    """
    pass


class NoIdleWorkersError(RubberException):
    """
    Indicates that we cannot kill any idle workers, none are idle
    """
    pass


class MinimumWorkersReached(RubberException):
    """
    Indicates that we are trying to terminate minimal levels of workers
    """
    pass


class UnknownHostError(RubberException):
    """
    Indicates that we cannot reach a given host.
    """
    host = None


class ConfigFormatError(RubberException):
    """
    Indicates that the format of a configuration file was not as expected.
    """
    pass


class NoTearDownTargets(RubberException):
    """
    Indicates that no idle workers could be taken down, perhaps because they
    are registered on the queue but not instanciated on the cloud. (?)
    """
    pass


class IncompatibleBackendError(RubberException):
    """
    Indicates that the Celery backend uses a broker type which is not
    supported by the current class.
    """
    pass


class NoProfilesFoundError(RubberException):
    """
    Indicates that rubber could not find any service profiles on which
    elasticity might be applied.
    """
    pass


class SGException(Exception):
    """
    Base exception class for ServiceGateway
    """
    pass


class MissingParameterError(SGException):
    """
    Missing parameter when calling ServiceGateway.
    """
    pass
