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

import os
import tempfile
from operator import itemgetter

import jinja2
# -- Standard lib ------------------------------------------------------------
import logging
import simplejson
import time
from VestaRestPackage.generic_rest_api import APP
# -- Project specific --------------------------------------------------------
from VestaRestPackage.request_authorisation import validate_authorisation
from VestaRestPackage.utility_rest import (request_wants_xml,
                                           get_request_url,
                                           submit_task,
                                           uuid_task,
                                           MissingParameterError,
                                           CELERY_APP,
                                           send_task_request,
                                           async_call,
                                           store_uuid)
from dicttoxml import dicttoxml
# -- 3rd party ---------------------------------------------------------------
from flask import request, jsonify, send_from_directory
from uuid import uuid4
from werkzeug import formparser
from werkzeug.utils import secure_filename

# Add the SG templates folder to the template loader directories
# (VRP one is used by default)
TEMPLATES_LOADER = jinja2.ChoiceLoader([
    APP.jinja_loader,
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                         'templates'))
])

SIMPLE_WORKFLOW = 'simple_workflow'
APP.jinja_loader = TEMPLATES_LOADER

# DIRTY FIX to prevent 'Request' object has no attribute 'is_xhr' bug.
# Fixed in recent versions of Flask.
APP.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

LOCAL_TEMPORARY_STORAGE = APP.config.get("LOCAL_TEMPORARY_STORAGE", {})
TEMPORARY_STORAGE_SIZE_LIMIT_GB = LOCAL_TEMPORARY_STORAGE.get('size_limit_gb', 10)
TEMPORARY_STORAGE_MAX_FILE_DURATION_SECONDS = LOCAL_TEMPORARY_STORAGE.get('max_file_duration_seconds', 86400)
TMP_DIR = os.path.join(tempfile.gettempdir(), "ServiceGateway")


def local_filename_to_url(filename, request):
    """
    Converts a local file path to url
    :param filename: name of the temporary file
    :param request: request object used to make the call
    :return: path to access the filename
    """
    return request.url_root + 'temporary_file/' + filename


def create_temporary_file_name(extension=None):
    """
    Creates a temporary file name

    :param extension: Extension to add to the file name. Ex: txt
    :return:
    """

    return str(uuid4()) + "." + str(extension) if extension else str(uuid4())


@APP.route("/temporary_upload_path", methods=['GET'])
def temporary_file_path():
    """
    GET a temporary upload path to which to send files.
    :param extension: optionally an extension to add to the file
    :return:
    """
    extension = request.args.get('extension', None)

    return local_filename_to_url(create_temporary_file_name(extension), request), 201


@APP.route("/temporary_file", methods=['POST'])
@APP.route("/temporary_file/<filename>", methods=['GET', 'POST'])
def add_file(filename=None):
    """
    POST a file to create a new temporary file on the server. A temporary file is stored for 24 hours or until the server
    reaches its storage capacity. This method should be used internally only.

    :param filename: Name of the file to be used in the url. If not supplied a UUID with a file extension
    will be generated. There is no guarantee that a file will not overwrite another existing file, thus use with caution
    names with caution.

    :return:    A url to access the file. The url path depends on the caller.
    """

    if request.method == 'POST':
        # make sure to have enough space
        clean_temporary_storage()

        stream, form, files = formparser.parse_form_data(request.environ,
                                                         stream_factory=custom_stream_factory)
        if len(files.keys()) != 1:
            return {"error": "Only one file should be supplied"}, 400
        else:
            filepath = files[files.keys()[0]].stream.name
            url = None
            if filename:
                filename = secure_filename(filename)
                new_path = os.path.join(os.path.dirname(filepath), filename)
                # Note that rename in 2.7 have the same functionality as replace in 3
                os.rename(filepath, new_path)
            else:
                filename = os.path.basename(filepath)

            url = local_filename_to_url(filename, request)
            return url, 201

    else:
        return send_from_directory(TMP_DIR, filename)


def custom_stream_factory(total_content_length, filename, content_type, content_length=None):
    extension = os.path.splitext(secure_filename(filename))[1]
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
    tmpfile = tempfile.NamedTemporaryFile('wb+', prefix=str(uuid4()), suffix=extension, dir=TMP_DIR
                                          , delete=False)
    return tmpfile


@APP.route("/simple_workflow/process", methods=['POST'])
def process_workflow():
    """
    POST a JSON structure to the service Gateway which partial contents will be
    passed on to the service.

    Requires:
    * a json field containing the following json { "services": [{service1} ...{serviceN}]} for chaining service execution
    * a file for each field referenced in the json section.
    * Temporary files which need to be created inside json field should have this format s__<number/GUID><.optional extension>__e
    :return:
    """
    logger = logging.getLogger(__name__)
    service_route = 'simple_workflow'
    service_name = SIMPLE_WORKFLOW

    validate_authorisation(request, APP.config["SECURITY"])

    stream, form, files = formparser.parse_form_data(request.environ,
                                                     stream_factory=custom_stream_factory)
    logger.info("JSON structure submitted at %s", service_route)

    # Hard coded at the moment since this is the only option we support
    stateful = False

    # overriden to read as a form structure
    multi_config = simplejson.loads(form['json']) if 'json' in form else None
    if multi_config is None:
        logger.error("Missing json parameter describing stateless execution parameter")
        return MissingParameterError('Missing json parameter describing stateless execution parameter'), 422
    else:
        logger.info("multi service json parameter contents : %s", multi_config)

    # make sure to have enough space
    clean_temporary_storage()

    # Replace existing files by path
    multi_json = simplejson.dumps(multi_config)
    for key in files.keys():
        filename = os.path.basename(files[key].stream.name)
        multi_json = multi_json.replace('"' + key + '"', '"' + local_filename_to_url(filename, request) + '"')

    multi_config = simplejson.loads(multi_json)

    worker_config = APP.config['WORKER_SERVICES'][service_name]
    celery_task_name = worker_config['celery_task_name']
    params = dict()
    # Added for compatibility but unused
    params['url'] = None
    params['name'] = celery_task_name
    params['app'] = CELERY_APP
    params['queue'] = worker_config['celery_queue_name']
    params['misc'] = multi_config
    params['misc']['stateful'] = stateful
    params['misc']['sg_url'] = request.url_root
    if request.headers.get('Authorization'):
        params['misc']['sg_token'] = request.headers.get('Authorization')

    logger.debug("Final param structure : %s", params)

    async_result = async_call(send_task_request, **params)

    friendly_task_name = '{0} by {1}'.format(celery_task_name, service_name)
    logger.info('"%s" task submitted -> UUID = %s',
                friendly_task_name, async_result.task_id)

    store_uuid(async_result.task_id, service_name)

    return jsonify({'uuid': async_result.task_id})


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

    # Save file locally

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


def clean_temporary_storage():
    files = get_tmp_files_to_delete()
    for f in files:
        os.remove(f[0])


def get_tmp_files_to_delete():
    """
    Return the temporary files which should be deleted due to either size of time restriction
    :return:    A list of files to delete
    """
    files = []
    for f in os.listdir(TMP_DIR):
        filepath = os.path.join(TMP_DIR, f)
        if os.path.isfile(filepath):
            files.append((filepath, os.path.getsize(filepath), os.path.getctime(filepath)))

    size_limit = TEMPORARY_STORAGE_SIZE_LIMIT_GB * 1024 * 1024 * 1024
    files = sorted(files, key=itemgetter(2))
    size = sum(f[1] for f in files)
    files_to_remove = []
    current_size = size
    # remove due to size
    while current_size > size_limit:
        file = files.pop()
        current_size -= file[1]
        files_to_remove.append(file)

    current_time = time.time()
    # remove due to time
    while len(files) > 0:
        if current_time - files[0][2] > TEMPORARY_STORAGE_MAX_FILE_DURATION_SECONDS:
            files_to_remove.append(files.pop(0))
        else:
            break

    return files_to_remove
