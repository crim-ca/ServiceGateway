#!/usr/bin/env python2.7
# coding:utf-8

# N.B. : Some of these docstrings are written in reSTructured format so that
# Sphinx can use them directly with fancy formatting.

"""
A REST API for Celery workers.

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
from flask import request, jsonify
from dicttoxml import dicttoxml
import jinja2

# -- Project specific --------------------------------------------------------
from VestaRestPackage.request_authorisation import validate_authorisation
from VestaRestPackage.generic_rest_api import APP, configure_home_route
from VestaRestPackage.utility_rest import (request_wants_xml,
                                           get_request_url,
                                           submit_task,
                                           uuid_task)
from . import __meta__  # Not really used here but __meta__ needs to be updated

# Add the SG templates folder to the template loader directories
# (VRP one is used by default)
TEMPLATES_LOADER = jinja2.ChoiceLoader([
    APP.jinja_loader,
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                         'templates'))
])
APP.jinja_loader = TEMPLATES_LOADER


@APP.route("/<service_route>/process", methods=['POST'])
@APP.route("/<service_route>/process/<storage_doc_id>", methods=['POST'])
def process(service_route, storage_doc_id=None):
    """
    POST a JSON structure to the service Gateway which partial contents will be
    passed on to the service.

    Optionnal keys are the following:

    :param storage_doc_id: The unique document ID of the file to transcode
       which can be found on the associated MSS. If not provided, a doc_url
       parameter must be submitted in the request
    :param doc_url: Document on which the processing will take place. Can be
       set to None if using the storage_doc_id argument or if there is no
       actual processing on a document.
    :param options: Will be used as a sub-structure which will be integrally
       passed on to the processing worker.
    """
    logger = logging.getLogger(__name__)

    validate_authorisation(request, APP.config["SECURITY"])

    logger.info("JSON structure submitted at %s", service_route)
    json_struct = request.get_json(silent=True)
    if json_struct is None:
        logger.info("No JSON structure supplied")
        json_struct = {}
    else:
        logger.info("JSON contents : %s", json_struct)

    if 'ann_doc_id' in request.values:
        ann_doc_id = request.values['ann_doc_id']
        args = {'ann_doc_id': ann_doc_id}
        ann_srv_url = get_request_url('POST_ANNOTATIONS_REQ_URL', args)
        logger.info("Will submit annotations to %s", ann_srv_url)
    else:
        ann_srv_url = None

    flag_noparams = False
    if 'noparams' in APP.config['WORKER_SERVICES'][service_route]:
        flag_noparams = \
            APP.config['WORKER_SERVICES'][service_route]['noparams']
        logger.debug("noparams = {}", flag_noparams)

    result = submit_task(storage_doc_id,
                         'annotate',
                         service_route,
                         ann_srv_url=ann_srv_url,
                         misc=json_struct,
                         no_params_needed=flag_noparams)
    return result


@APP.route("/<service_route>/annotate", methods=['POST'])
@APP.route("/<service_route>/annotate/<storage_doc_id>", methods=['POST'])
def annotate(service_route, storage_doc_id=None):
    """
    POST a processing request through a form

    In the POST multi-part form document upload there can be a field called
    payload which contents will be passed onto the worker itself.

    :param storage_doc_id: The unique document ID of the file to transcode.
                           If not provided, a doc_url parameter must be
                           submitted in the request
    :param service_route: Route name of the service e.g.:
                          ['diarisation', 'STT', etc.]
    :return: JSON object with the task uuid or error response.
    """
    logger = logging.getLogger(__name__)

    validate_authorisation(request, APP.config["SECURITY"])

    # request.values combines values from args and form
    if 'ann_doc_id' in request.values:
        ann_doc_id = request.values['ann_doc_id']
        args = {'ann_doc_id': ann_doc_id}
        ann_srv_url = get_request_url('POST_ANNOTATIONS_REQ_URL', args)
        logger.info("Will submit annotations to %s", ann_srv_url)
    else:
        ann_srv_url = None

    logger.info("Got a annotation request with parameters %s",
                request.values)

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
        validate_authorisation(request, APP.config["SECURITY"])
    logger.info("Got %s request for %s", task, service_route)
    state = uuid_task(task, service_route)

    if request_wants_xml():
        logger.debug("Rendering result as XML")
        r_val = dicttoxml(state, attr_type=False, custom_root="process_status")
    else:
        logger.debug("Rendering result as JSON")
        r_val = jsonify(state)
    return r_val
