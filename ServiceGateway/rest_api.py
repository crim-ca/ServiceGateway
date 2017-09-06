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
from VestaService.request_process_mesg import send_task_request

from VestaRestPackage.request_authorisation import validate_authorisation
from VestaRestPackage.generic_rest_api import APP, configure_home_route


# submit_task commented out because its clone mysubmit_task(), inserted below, is used by process()
from VestaRestPackage.utility_rest import (request_wants_xml,
                                           get_request_url,
                                           #submit_task,
					   validate_service_route, validate_url, store_uuid, log_request, async_call, 
                                           uuid_task)

from VestaRestPackage.app_objects import CELERY_APP
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
	
    logger.info("json-submit-feature: JSON structure submitted at %s", service_route)
    json_struct = request.get_json(silent=True)
    if json_struct is None:
        print("No JSON struct supplied")
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
	flag_noparams = APP.config['WORKER_SERVICES'][service_route]['noparams']
       	print("noparams = {}".format(flag_noparams))
	

    result = mysubmit_task(storage_doc_id,
        	                 'annotate',
                	         service_route,
                        	 ann_srv_url=ann_srv_url,
	                         misc=json_struct,
				 no_params_needed = flag_noparams)
    return result


def mysubmit_task(storage_doc_id, task_name, service_route='.', no_params_needed=False,**extra_params):
    """
    Submit a task to a worker.

    :param storage_doc_id: The document ID for which a task should be run.
    :param task_name: The task name for logging purposes
    :param service_route: service route to obtain the requested service name
    :param extra_params: Extra parameters that are passed to send_task_request
    :returns: JSON object with the task UUID or error response.
    :raises: :py:exc:`~.vesta_exceptions.MissingParameterError`
    """
    logger = logging.getLogger(__name__)
    service_name = validate_service_route(service_route)
    params = extra_params
    logger.debug("Extra params are : %s", params)

    print("no_params_needed = {}".format(no_params_needed))

    if service_route == '.':
        friendly_task_name = task_name
    else:
        friendly_task_name = '{0} by {1}'.format(task_name, service_name)

    if storage_doc_id is None:
	doc_url = None
	if not no_params_needed:
	    # If storage_doc_id is None a full doc_url must be given
            if 'doc_url' not in request.values:
               raise MissingParameterError('POST',
                                           '/{0}'.format(task_name),
                                           'doc_url')

	    else:
            # request.values combines values from arguments and form
               doc_url = request.values['doc_url']

        logger.info('Submitting "%s" task with public url : %s',
                    friendly_task_name, doc_url)
    else:
        doc_url = get_request_url('GET_STORAGE_DOC_REQ_URL',
                                  {'storage_doc_id': storage_doc_id})

        logger.info('Submitting "%s" task with storage doc id : %s',
                    friendly_task_name, storage_doc_id)

    if no_params_needed is False:
	 validate_url(doc_url)

    # For all storage_*_id given in request.values, resolve them if necessary
    # and add them to the misc data holder to async_call
    def is_storage_arg(x):
        return x.startswith('storage_') and x.endswith('_id')

    def is_url_arg(x):
        return x.endswith('_url') and x != 'doc_url'

    storage_args = list(filter(is_storage_arg, list(request.values.keys())))
    url_args = list(filter(is_url_arg, list(request.values.keys())))

    if 'misc' not in params:
        logger.debug("Initialising empty dict for absent misc structure")
        params['misc'] = {}

    if storage_args or url_args:
        logger.debug("%s arguments referencing storage ids: %s",
                     len(storage_args), storage_args)

        for storage_arg in storage_args:
            url_ = None
            # E.g.: If "storage_txt_id" then doctype == 'txt'
            doctype = storage_arg.split('_')[1]
            direct_url_arg = "{0}_url".format(doctype)
            if direct_url_arg in list(request.values.keys()):
                # Here we could also consider raising an exception.
                logger.warning("Conflicting arguments %s and %s, "
                               "defaulting to %s".
                               storage_arg, direct_url_arg, direct_url_arg)
                # Preference given to the direct URL
                url_ = request.values[direct_url_arg]
            else:
                id_ = request.values[storage_arg]
                url_ = get_request_url('GET_STORAGE_DOC_REQ_URL',
                                       {'storage_doc_id': id_})
                logger.debug("Resolving URL for id %s of type %s: %s",
                             id_, doctype, url_)

            validate_url(url_)
            logger.info("Using argument %s=%s", storage_arg, url_)
            params['misc'][direct_url_arg] = url_

        # For all *_url given in request.values, add them to the misc data
        # holder to async_call
        logger.debug("%s arguments referencing direct URLs other than"
                     " doc_url: %s", len(url_args), url_args)
        for url_arg in url_args:
            url_ = request.values[url_arg]
            validate_url(url_)
            logger.info("Using argument %s=%s", url_arg, url_)
            params['misc'][url_arg] = url_

    log_request(service_name, 'POST {request} request on {doc_url}'
                .format(request=task_name, doc_url=doc_url))

    other_args = {}
    for key, value in request.values.items():
        if not is_storage_arg(key) and not is_url_arg(key):
            other_args[key] = value

    # Add this so that all workers can know where the default associated
    # storage server is located.
    other_args['upload_url'] = APP.config['POST_STORAGE_DOC_REQ_URL']
    logger.debug("Other arbitrary arguments: %s", other_args)

    worker_config = APP.config['WORKER_SERVICES'][service_name]
    celery_task_name = worker_config['celery_task_name']
    params['url'] = doc_url
    params['name'] = celery_task_name
    params['app'] = CELERY_APP
    params['queue'] = worker_config['celery_queue_name']
    params['misc'].update(other_args)
    logger.debug("Final param structure : %s", params)
    async_result = async_call(send_task_request, **params)

    logger.info('"%s" task submitted for %s -> UUID = %s',
                friendly_task_name, doc_url, async_result.task_id)

    store_uuid(async_result.task_id, service_name)

    return jsonify({'uuid': async_result.task_id})











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

    result = mysubmit_task(storage_doc_id, 'annotate', service_route,
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
