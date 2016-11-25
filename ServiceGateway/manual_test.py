#!/usr/bin/env python
# coding: utf-8

"""
Manual integration test utilities.

Can also be useful to simulate client access to the LoadBalancer and associated
optional co-services such as the JSON Annotations Storage Server and the
Multimedia Storage Server.

Generally useful for deployment integration tests.
"""

# -- Standard Library --------------------------------------------------------
from os.path import abspath, dirname, join, basename
from tempfile import NamedTemporaryFile
from time import sleep
import logging.config
import optparse
import logging
import json
import os

# -- 3rd party ---------------------------------------------------------------
import requests

# -- Project specific --------------------------------------------------------
from .VestaRestPackage.jwt_ import generate_token
from .VestaRestPackage.app_objects import APP

# -- Configuration shorthands ------------------------------------------------
THIS_DIR = abspath(dirname(__file__))
BASE_URL = "http://{s}".format(s=APP.config['MY_SERVER_NAME'])

# TODO : Edit or override according to deployment:
# LB_URL = "{b}/vlb".format(b=BASE_URL)
LB_URL = "{b}:5000".format(b=BASE_URL)

JASS_URL = APP.config['POST_ANNOTATIONS_REQ_URL'].split('/document/')[0]
MSS_URL = APP.config['GET_STORAGE_DOC_REQ_URL'].split('/get/')[0]

TEST_DOC = join(THIS_DIR, "test_data/1184_103_short.wav")
TEST_TXT_DOC = join(THIS_DIR, "test_data/1184_103.txt")
SERVICES = APP.config['WORKER_SERVICES'].keys()
CHUNK_SIZE = 1024
BATCH_REQ_SIZE = 10


# -- JASS --------------------------------------------------------------------
def create_ann_doc(data=None):
    """
    Create annotation document
    """
    logger = logging.getLogger(__name__)
    if not data:
        data = {"@context": "test", "a": "a", "b": "b"}
    headers = {'Content-Type': "application/json"}
    resp = requests.post("{u}/document".format(u=JASS_URL),
                         data=json.dumps(data),
                         headers=headers)
    logger.info("Response : {r}".format(r=resp))
    resp_json = resp.json()
    doc_id = resp_json['id']
    logger.info("doc id : {0}".format(doc_id))
    return doc_id


def get_ann_doc(doc_id):
    """
    Get contents of annotation storage document (not annotations)
    """
    logger = logging.getLogger(__name__)
    resp = requests.get("{u}/document/{i}".format(JASS_URL, i=doc_id))
    logger.info("Response : {r}".format(r=resp))
    return resp.json()


def get_annotations(doc_id):
    """
    Get annotations.
    """
    logger = logging.getLogger(__name__)
    resp = requests.get("{u}/document/{i}/annotations".format(u=JASS_URL,
                                                              i=doc_id))
    logger.info("Response : {r}".format(r=resp))
    return resp.json()


# -- MSS ---------------------------------------------------------------------
def upload_doc(file_path):
    """
    Upload a document to MSS
    """
    logger = logging.getLogger(__name__)
    filename = basename(file_path)
    params = {'filename': filename}
    resp = requests.get("{u}/add".format(u=MSS_URL), params=params)
    logger.info("Response : {r}".format(r=resp))
    resp_json = resp.json()
    logger.info("body: {b}".format(b=resp.text))
    storage_doc_id = resp_json['storage_doc_id']
    upload_url = resp_json['upload_url']
    data = open(file_path, 'rb')
    resp = requests.put(upload_url, data=data)
    logger.info("Response : {r}".format(r=resp))
    logger.info("body: {b}".format(b=resp.text))
    return storage_doc_id


def get_doc(storage_doc_id):
    """
    Download document from MSS

    Deletion of the resulting file is of the responsibility of the caller.
    """
    logger = logging.getLogger(__name__)
    resp = requests.get("{u}/get/{s}".format(u=MSS_URL, s=storage_doc_id))
    logger.info("Response : {r}".format(r=resp))
    with NamedTemporaryFile(delete=False, mode='wb+') as file__:
        for chunk in resp.iter_content(CHUNK_SIZE):
            file__.write(chunk)
        logger.info("Contents in {f}".format(f=file__.name))


# -- Annotator ---------------------------------------------------------------
def annotate_service(service_name, storage_doc_id, params):
    """
    Run tests for a given service.
    """
    logger = logging.getLogger(__name__)
    logger.info("Running tests for {0}".format(service_name))
    logger.info("Getting token")

    token = generate_token()

    header = {"content-type": 'application/json',
              "Authorization": token}
    resp = requests.post("{u}/{s}/annotate/{d}".
                         format(u=LB_URL,
                                s=service_name,
                                d=storage_doc_id),
                         headers=header,
                         params=params)
    logger.info("Response : {r}".format(r=resp))
    logger.info("body: {b}".format(b=resp.text))
    resp_json = resp.json()
    uuid = resp_json['uuid']
    logger.info("uuid: {u}".format(u=uuid))
    return uuid


def status_service(service_name, uuid):
    """
    Get status of request
    """
    logger = logging.getLogger(__name__)
    params = {'uuid': uuid}
    resp = requests.get("{u}/{s}/status".
                        format(u=LB_URL, s=service_name),
                        params=params)
    logger.info("Response : {r}".format(r=resp))
    logger.info("body: {b}".format(b=resp.text))
    resp_json = resp.json()
    return resp_json['status']


class ServiceError(Exception):
    """
    Indicates that there was an error with the service use.
    """
    pass


def main():
    """
    Script entry point

    Sends test file to MSS, tells annotation workers to get them from MSS,
    process, and send to JASS.

    Iterates over multiple workers.
    """
    logger = logging.getLogger('VestaLoadBalancer')
    parser = optparse.OptionParser()

    log_conf_fn = os.path.join(THIS_DIR, 'logging.ini')
    parser.add_option("-l",
                      action='store',
                      default=log_conf_fn,
                      dest='logging_conf_fn',
                      help='Set logging configuration filename')

    options = parser.parse_args()[0]

    logging.config.fileConfig(options.logging_conf_fn)

    ann_doc_id = create_ann_doc()
    storage_doc_id = upload_doc(TEST_DOC)

    for service_name in SERVICES:
        params = {'ann_doc_id': ann_doc_id}
        if service_name == 'matching':
            storage_txt_id = upload_doc(TEST_TXT_DOC)
            params['storage_txt_id'] = storage_txt_id

        uuid = annotate_service(service_name, storage_doc_id, params)
        status = None
        while status != "SUCCESS":
            logger.info("Waiting")
            sleep(3)
            status = status_service(service_name, uuid)
            if status == "FAILURE":
                raise ServiceError(status)

        logger.info("status : {s}".format(s=status))

    annotations = get_annotations(ann_doc_id)
    logger.info("Annotations: {a}".format(a=annotations))

    # TODO : Delete annotations document on JASS.

if __name__ == '__main__':
    main()
