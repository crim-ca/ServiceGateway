#!/usr/bin/env python2
# coding: utf-8

"""
Manual integration test utilities.

Can also be useful to simulate client access to the LoadBalancer and associated
optional co-services such as the JSON Annotations Storage Server and the
Multimedia Storage Server.

Generally useful for deployment integration tests.
"""

# -- Standard Library --------------------------------------------------------
from os.path import abspath, dirname, basename
from tempfile import NamedTemporaryFile
from time import sleep
import logging.config
import optparse
import logging
import json
import os

# -- 3rd party ---------------------------------------------------------------
from requests import post, put, get

# -- Project specific --------------------------------------------------------
from VestaLoadBalancer.VestaRestPackage.jwt_ import generate_token
from VestaLoadBalancer.VestaRestPackage.app_objects import APP
from .exceptions import ServiceError, UnknownService

# -- Configuration shorthands ------------------------------------------------
THIS_DIR = abspath(dirname(__file__))
LB_URL = "http://{s}".format(s=APP.config['MY_SERVER_NAME'])

JASS_URL = APP.config['POST_ANNOTATIONS_REQ_URL'].split('/document/')[0]
MSS_URL = APP.config['GET_STORAGE_DOC_REQ_URL'].split('/get/')[0]

# You need to define which services you'll want to test in the config file.
S_CONF = APP.config['SERV_TEST_CONF']

CHUNK_SIZE = 1024
BATCH_REQ_SIZE = 10


# -- JASS --------------------------------------------------------------------
def create_ann_doc(data=None):
    """
    Create annotation document
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating annotation document")
    logger.debug("Annotation document Data : %s", data)
    if not data:
        data = {"@context": "test", "a": "a", "b": "b"}
    headers = {'Content-Type': "application/json"}
    resp = post("{u}/document".format(u=JASS_URL),
                data=json.dumps(data),
                headers=headers)
    logger.info("Annotation creation response : %s", resp)
    resp.raise_for_status()
    resp_json = resp.json()
    doc_id = resp_json['id']
    logger.info("Annotation doc id : %s", doc_id)
    return doc_id


def get_ann_doc(doc_id):
    """
    Get contents of annotation storage document (not annotations)
    """
    logger = logging.getLogger(__name__)
    resp = get("{u}/document/{i}".format(JASS_URL, i=doc_id))
    logger.info("Get annotation doc response : %s", resp)
    resp.raise_for_status()
    return resp.json()


def get_annotations(doc_id):
    """
    Get annotations.
    """
    logger = logging.getLogger(__name__)
    resp = get("{u}/document/{i}/annotations".format(u=JASS_URL, i=doc_id))
    logger.info("Get annotation response : %s", resp)
    resp.raise_for_status()
    return resp.json()


# -- MSS ---------------------------------------------------------------------
def mss_get_upload_url(file_path):
    """
    Obtain an upload URL for a new document on the MSS.

    :returns: Tuple with storage doc id and storage URL for upload purposes.
    """
    logger = logging.getLogger(__name__)

    signature_key = APP.config['SECURITY']['JWT']['JWT_SIGNATURE_KEY']
    audience = APP.config['SECURITY']['JWT']['JWT_AUDIENCE']
    algorithm = APP.config['SECURITY']['JWT']['JWT_ALGORITHM']
    token = generate_token(signature_key, audience, algorithm, duration=600)

    logger.info("Obtaining upload URL for MSS")
    header = {"content-type": 'application/json',
              "Authorization": token}
    filename = basename(file_path)
    params = {'filename': filename}
    logger.debug("MSS URL is %s", MSS_URL)
    resp = get("{u}/add".format(u=MSS_URL), params=params, headers=header)
    logger.info("MSS GET/add response : %s", resp)
    resp.raise_for_status()
    resp_json = resp.json()
    logger.info("body: %s", resp.text)
    storage_doc_id = resp_json['storage_doc_id']
    upload_url = resp_json['upload_url']
    return (storage_doc_id, upload_url)


def upload_doc_post(file_path):
    """
    Upload a document to MSS
    """
    logger = logging.getLogger(__name__)
    logger.debug("Uploading file %s", file_path)
    # storage_doc_id, upload_url = mss_get_upload_url(file_path)
    upload_url = APP.config['POST_STORAGE_DOC_REQ_URL']
    files = {'file': open(file_path, 'rb')}
    logger.info("Putting document contents")
    resp = post(upload_url, files=files)
    logger.info("POST to MSS response : %s", resp)
    logger.info("POST to MSS body: {b}".format(b=resp.text))
    resp.raise_for_status()
    return resp.json()['storage_doc_id']


def delete(storage_doc_id):
    """
    Delete a document from the MSS.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Deleting file from MSS %s", storage_doc_id)
    resp = post("{u}/delete/{s}".format(u=MSS_URL, s=storage_doc_id))
    logger.info("POST to delete on MSS response : %s", resp)
    resp.raise_for_status()
    return resp


def upload_doc(file_path):
    """
    Upload a document to MSS

    Deletion of the resulting file is of the responsibility of the caller.
    """
    logger = logging.getLogger(__name__)
    storage_doc_id, upload_url = mss_get_upload_url(file_path)
    data = open(file_path, 'rb')
    resp = put(upload_url, data=data)
    logger.info("PUT to MSS response : %s", resp)
    logger.info("PUT to MSS body: %s", resp.text)
    resp.raise_for_status()
    return storage_doc_id


def get_doc(storage_doc_id):
    """
    Download document from MSS
    """
    logger = logging.getLogger(__name__)
    resp = get("{0}/get/{1}".format(MSS_URL, storage_doc_id))
    logger.info("GET to get on MSS response : %s", resp)
    resp.raise_for_status()
    with NamedTemporaryFile(delete=False, mode='wb+') as file__:
        for chunk in resp.iter_content(CHUNK_SIZE):
            file__.write(chunk)
        logger.info("Contents in %s", file__.name)
    return resp


# -- Annotator ---------------------------------------------------------------
def annotate_url(service_name, url, params):
    """
    Run tests for a given service.
    """
    logger = logging.getLogger(__name__)
    logger.info("Running tests for %s".format(service_name))
    logger.info("SG address is %s", LB_URL)

    logger.info("Getting token")
    signature_key = APP.config['SECURITY']['JWT']['JWT_SIGNATURE_KEY']
    audience = APP.config['SECURITY']['JWT']['JWT_AUDIENCE']
    algorithm = APP.config['SECURITY']['JWT']['JWT_ALGORITHM']
    token = generate_token(signature_key, audience, algorithm, duration=600)

    params['doc_url'] = url
    header = {"content-type": 'application/json',
              "Authorization": token}
    resp = post("{u}/{s}/annotate".format(u=LB_URL, s=service_name),
                headers=header,
                params=params)
    logger.info("POST to annotate response : %s", resp)
    logger.info("POST to annotate body: %s", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    uuid = resp_json['uuid']
    logger.info("Annotation UUID: %s", uuid)
    return uuid


def annotate_service(service_name, storage_doc_id, params):
    """
    Run tests for a given service.
    """
    logger = logging.getLogger(__name__)
    logger.info("Running tests for %s", service_name)
    logger.info("SG address is %s", LB_URL)
    logger.info("Getting token")
    logger.debug("Params are : %s", params)

    signature_key = APP.config['SECURITY']['JWT']['JWT_SIGNATURE_KEY']
    audience = APP.config['SECURITY']['JWT']['JWT_AUDIENCE']
    algorithm = APP.config['SECURITY']['JWT']['JWT_ALGORITHM']
    token = generate_token(signature_key, audience, algorithm, duration=600)

    header = {"content-type": 'application/json',
              "Authorization": token}
    resp = post("{u}/{s}/annotate/{d}".
                format(u=LB_URL,
                       s=service_name,
                       d=storage_doc_id),
                headers=header,
                params=params)
    logger.debug("POST request URL: %s", resp.url)
    logger.info("POST to annotation document response : %s", resp)
    logger.info("POST to annotation document body: %s", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    uuid = resp_json['uuid']
    logger.info("Annotation UUID: %s", uuid)
    return uuid


def transcode(doc_uuid):
    """
    Launch transcoding of given document.
    """
    logger = logging.getLogger(__name__)
    logger.info("Launching transcoding request")

    signature_key = APP.config['SECURITY']['JWT']['JWT_SIGNATURE_KEY']
    audience = APP.config['SECURITY']['JWT']['JWT_AUDIENCE']
    algorithm = APP.config['SECURITY']['JWT']['JWT_ALGORITHM']
    token = generate_token(signature_key, audience, algorithm, duration=600)

    header = {"content-type": 'application/json',
              "Authorization": token}

    resp = post("{u}/transcode/{d}".
                format(u=MSS_URL,
                       d=doc_uuid),
                headers=header)

    logger.info("Launch transcoding response : %s", resp)
    logger.info("Launch transcoding body: %s", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    uuid = resp_json['uuid']
    logger.info("Transcoding request UUID: %s", uuid)
    return uuid


def status_service(service_name, uuid):
    """
    Get status of request
    """
    logger = logging.getLogger(__name__)
    params = {'uuid': uuid}
    resp = get("{u}/{s}/status".format(u=LB_URL, s=service_name),
               params=params)
    logger.debug("Status response : %s", resp)
    logger.debug("Status body: %s", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    status = resp_json['status']
    if status == 'FAILURE':
        logger.warning(resp_json)
    return status


def status_transcode(uuid):
    """
    Get status of request
    """
    logger = logging.getLogger(__name__)
    params = {'uuid': uuid}
    resp = get("{u}/status".format(u=MSS_URL),
               params=params)
    logger.debug("Transcode request response : %s", resp)
    logger.debug("Transcode request body: %s", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    return resp_json['status']


def main():
    """
    Script entry point

    Sends test file to MSS, tells annotation workers to get them from MSS,
    process, and send to JASS.

    Iterates over multiple workers.
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

    ann_doc_id = create_ann_doc()
    graph_doc_id = None
    for service_name in S_CONF:
        logger.info("Running tests for service %s", service_name)
        params = {'ann_doc_id': ann_doc_id}
        logger.info("Using document parameters : %s", S_CONF[service_name])
        if service_name == 'matching':
            storage_txt_id = upload_doc(S_CONF[service_name]['test_txt_doc'])
            storage_doc_id = upload_doc(S_CONF[service_name]['test_doc'])
            params['storage_txt_id'] = storage_txt_id
        elif service_name == 'SPV':
            logger.info("Creating SPV document on MSS")
            storage_doc_id = upload_doc(S_CONF[service_name]['test_doc'])
            logger.debug("SPV source document has id = %s", storage_doc_id)
            graph_doc_id, dest_doc_url = mss_get_upload_url('SPV_graph.zip')
            params['dest_doc'] = dest_doc_url
            logger.info("SPV resulting graph will be sent to URL : %s",
                        dest_doc_url)
            logger.info("SPV resulting graph ID will be : %s", graph_doc_id)
        elif service_name == 'STT':
            if 'SPV' in S_CONF:  # Should be a previously called service.
                graph_url = "{0}/get/{1}".format(MSS_URL, graph_doc_id)
                params['spv_graph'] = graph_url
            storage_doc_id = upload_doc(S_CONF[service_name]['test_doc'])
        elif service_name in ['diarisation', 'transition', 'faceanalysis']:
            # Vanilla setup.
            storage_doc_id = upload_doc(S_CONF[service_name]['test_doc'])
        else:
            raise UnknownService(service_name)

        uuid = annotate_service(service_name, storage_doc_id, params)
        status = None
        while status != "SUCCESS":
            logger.info("Waiting")
            sleep(5)
            status = status_service(service_name, uuid)
            if status == "FAILURE":
                raise ServiceError(status)

        logger.info("status : %s", status)

    logger.info("Getting annotations")
    annotations = get_annotations(ann_doc_id)
    logger.info("Annotations : %s", annotations)

    # TODO : Delete annotations document on JASS and doc on MSS.

if __name__ == '__main__':
    main()
