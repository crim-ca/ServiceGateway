#!/usr/bin/env python
# coding:utf-8

# N.B. : Some of these docstrings are written in reSTructured format so that
# Sphinx can use them directly with fancy formatting.

"""
This module defines a REST API for the load balancer as defined by the CANARIE
API specification. See :
https://collaboration.canarie.ca/elgg/file/download/849

Any incoming request on the REST interface is passed on to the Celery
distributed worker queue and any service workers listening on the corresponding
queue should pick up the request message and initiate their task.

From a code separation perspective this module is in charge of defining the
REST API and use others modules to do the actual job. It also plays the role of
formatting any response that should be sent back in the proper format.
"""


# -- Standard lib ------------------------------------------------------------
import logging
import os

# -- 3rd party ---------------------------------------------------------------
from flask import request
import jinja2

# -- Project specific --------------------------------------------------------
from .VestaRestPackage.generic_rest_api import configure_home_route
from .VestaRestPackage.utility_rest import get_request_url
from .VestaRestPackage.utility_rest import submit_task
from .VestaRestPackage.utility_rest import uuid_task
from .VestaRestPackage.generic_rest_api import APP
from .VestaRestPackage.jwt_ import validate_token

# Add the VLB templates folder to the template loader directories
# (VRP one is used by default)
TEMPLATES_LOADER = jinja2.ChoiceLoader([
    APP.jinja_loader,
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                         'templates'))
])
APP.jinja_loader = TEMPLATES_LOADER


@APP.route("/<service_route>/annotate", methods=['POST'])
@APP.route("/<service_route>/annotate/<storage_doc_id>", methods=['POST'])
def annotate(service_route, storage_doc_id=None):
    """
    POST a transcoding request through a form

    :param storage_doc_id: The unique document ID of the file to transcode.
                           If not provided, a doc_url parameter must be
                           submitted in the request
    :param service_route: Route name of the service e.g.:
                          ['diarisation', 'STT', etc.]
    :return: JSON object with the task uuid or error response.
    """
    logger = logging.getLogger(__name__)

    logger.debug(u"Validating token")
    signed_token = request.headers.get('Authorization')
    logger.debug(u"Request headers are : {0}".format(request.headers))
    validate_token(signed_token)

    # request.values combines values from args and form
    if 'ann_doc_id' in request.values:
        ann_doc_id = request.values['ann_doc_id']
        args = {'ann_doc_id': ann_doc_id}
        ann_srv_url = get_request_url('POST_ANNOTATIONS_REQ_URL', args)
        logger.debug("Will submit annotations to {u}".format(u=ann_srv_url))
    else:
        ann_srv_url = None

    logger.info(u"Got a annotation request with parameters "
                u"storage_doc_id={s} service={sn} ann_srv_url={au}"
                .format(s=storage_doc_id, sn=service_route, au=ann_srv_url))

    result = submit_task(storage_doc_id, 'annotate', service_route,
                         ann_srv_url=ann_srv_url)
    return result


@APP.route("/<service_route>/<any(status,cancel):task>")
def uuid_task_route(service_route, task):
    """
    GET the status or cancel a task identified by a uuid.

    :param task: status or cancel
    :param service_route: Route name of the service e.g.:
                          ['diarisation', 'STT', etc.]
    :returns: JSON object with latest status or error response.
    """
    logger = logging.getLogger(__name__)

    if task == 'cancel':
        logger.debug(u"Validating token")
        signed_token = request.headers.get('Authorization')
        logger.debug(u"Request headers are : {0}".format(request.headers))
        validate_token(signed_token)

    logger.info(u"Got {t} request for {s}".format(t=task, s=service_route))
    return uuid_task(task, service_route)


if __name__ != "__main__":
    configure_home_route()
