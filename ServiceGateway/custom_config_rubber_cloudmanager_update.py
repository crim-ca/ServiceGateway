# coding: utf-8

"""
Default configuration values for service gateway package.

Copy this file, rename it if you like, then edit to keep only the values you
need to override for the keys found within.

To have the programs in the package override the values with the values
found in this file, you need to set the environment variable named
"VRP_CONFIGURATION" to the path of your own copy before launching the program.

See also :py:mod:`VestaRestPackage.print_example_configuration`.
"""

from os.path import dirname, join
import os
import re

__THIS_DIR__ = dirname(__file__)


MY_SERVER_NAME = "localhost"

# Database name relative to the current application directory
DATABASES = {
    'Invocations': {
        'filename': "service_invocations.db",
        'schema_filename':
            join(__THIS_DIR__, "db_struct/service_invocations_schema.sql")},
    'Requests': {
        'filename': "requests.db",
        'schema_filename':
            join(__THIS_DIR__, "db_struct/requests_schema.sql")}}


RUBBER_BACKORDER_THRESHOLD = 0
RUBBER_MAX_VM_QTY = 6  # Maximum number of Virtual machines we can spawn.
RUBBER_MAX_STORAGE = 1000  # Max storage allowed for VM spawn by rubber (Gb)
RUBBER_MAX_RAM = 100  # MAX Ram allowed for rubber for VM spawn by rubber (Gb)
# Default seconds to wait between elasticity evaluations:
RUBBER_EVAL_INTERVAL = 2 #120
RUBBER_MIN_IDLE_WORKERS = 1
# Time after which a non-functional VM will be terminated:
RUBBER_SLACKER_TIME_THRESHOLD = 300


CELERY_PROJ_NAME = "worker"
BROKER_HOST = os.getenv('AMQP_HOST', 'localhost')
BROKER_ADMIN_PORT = '15672'
BROKER_ADMIN_UNAME = os.getenv('AMQP_USERNAME', 'test')
BROKER_ADMIN_PASS = os.getenv('AMQP_PASSWORD', 'asdf')
BROKER_PORT = os.getenv('AMQP_PORT', '5672')

CELERY = {
    'BROKER_URL': "amqp://"+BROKER_ADMIN_UNAME+":"+BROKER_ADMIN_PASS+"@"+BROKER_HOST+":"+BROKER_PORT+"//",
    'CELERY_RESULT_BACKEND': "amqp://",
    'CELERY_TASK_SERIALIZER': "json",
    'CELERY_RESULT_SERIALIZER': "json",
    'CELERY_ACCEPT_CONTENT': ["json"],
    'CELERY_SEND_EVENTS': True,
    'CELERYD_PREFETCH_MULTIPLIER': 4,
    'CELERY_TASK_RESULT_EXPIRES': 7200}

flower_host = os.getenv('FLOWER_HOST', "localhost")
FLOWER_API_URL = 'http://{}:5555/api'.format(flower_host)

# -- CLOUD CONFIG --
cloud_name = os.getenv('CLOUD_NAME', 'CLOUD_UNNAMED')
cloud_auth_url = os.getenv('CLOUD_AUTH_URL', 'http://10.1.30.100:5000/v2.0')# 'http://ops-ctrl.cloud.corpo.crim.ca:5000/v3')
cloud_username = os.getenv('CLOUD_USER_NAME', 'guest')
cloud_password = os.getenv('CLOUD_PASSWORD', 'guest')

try:
    cloud_init_file_path = os.getenv('CLOUD_INIT_FILE_PATH','cloud_init.template')
    with open(cloud_init_file_path, 'r') as cloud_init_file:
        cloud_init_file_content = cloud_init_file.read()

    # replace every $var in cloud_init_file_content by their environment variable
    envars = re.findall("\$(\w+[A-Z])", cloud_init_file_content)
    for envar in envars:
        cloud_init_file_content = cloud_init_file_content.replace('$'+envar, os.getenv(envar, '$'+envar))
    cloud_init_file_content = [cloud_init_file_content]
except:
    cloud_init_file_content = []

# OpenStack access configuration.
OPS_CONFIG = {'name': cloud_name,
              'cloud_type': 'OpenStack',  # Important so we use the right API.
              'networks': ['cloud-int_net', 'RD_Int_local_net', 'cloud-ext_net'],  # List of network available
              'security_group': ["default"],
              'username': cloud_username,
              'password': cloud_password,
              'tenant_name': 'RD_Int',
              'auth_url': cloud_auth_url,
              'vm_slots': RUBBER_MAX_VM_QTY,
              'storage': RUBBER_MAX_STORAGE,
              'memory': RUBBER_MAX_RAM,
              'key_name': 'ogc_test',#'ogc-new-openstack',
              'user_domain_name': 'CORPO',
              'project_domain_name': 'CORPO'}



# -- WORKER CONFIG --

WORKER_SERVICES = {
            'joblauncher_tiny': {
                # Keyword used in the rest API to access this service
                # (ex.: http://server/<route_keyword>/info)
                # Set to '.' to access this service without keyword
                # (ex.: http://server/info)
                'route_keyword': 'joblauncher_tiny',

                # The celery task name.
                # Must match the task in the worker APP name :
                # <proj_name>.<task_name>
                # (ex.: worker.my_service)
                'celery_task_name': 'joblauncher',

                # The celery queue name.
                # Must match the queue name specified when starting the worker
                # (by the -Q switch)
                'celery_queue_name': 'celery_tiny',

                # Following parameters are required by the CANARIE API (info
                # request)
                'name': 'joblauncher_tiny',
                'synopsis': "RESTful service providing my_service.",
                'version': "0.1.0",  # Expected version - will check.
                'institution': 'My Organisation',
                'releaseTime': '2015-01-01T00:00:00Z',
                'supportEmail': 'support@my-organisation.ca',
                'category': "Data Manipulation",
                'researchSubject': "My research subject",
                'tags': "joblauncher, research",

                'home': "http://www.google.com",
                'doc': "http://www.google.com",
                'releasenotes': "http://www.google.com",
                'support': "http://www.google.com",

                # If the source are not provided, CANARIE requires a 204 (No
                # content) response
                'source': ",204",
                'tryme': "http://www.google.com",
                'licence': "http://www.google.com",
                'provenance': "http://www.google.com",
                'os_args': {'vm_image': {cloud_name: 'ogc_celery_docker'},# '89c02c61-4c4f-4e30-bf40-cf7722738487'},
                            'vm_type': 'm1.tiny',
                            'instance_type': {cloud_name: 'm1.tiny'},
                            'vm_user': cloud_username,
                            'vm_networkassoc': 'rd_int_net201',
                            'vm_mem': 8,
                            'vm_cores': 1,
                            'vm_storage': 10,
                            'pre_customization': cloud_init_file_content
                            },
                # Process-request to spawn VM ratio
                'rubber_params': {'spawn_ratio': 1}
            },
}




# -- OTHER --

REQUEST_REGISTER_FN = "static/requests.shelve"
# security section. For tests without security, put
# SECURITY = {"BYPASS_SECURITY": True}
SECURITY = {
    # Needed for workers to call VLB to obtain resources:
    'AUTHORISATION_KEY': "aed9yhfapgaegaeg",
    # Used to configure JSON web token.
    'JWT': {
        'JWT_SIGNATURE_KEY': "vJmMvm44x6RJcVXNPy6UDcSfJHOHNHrT1tKpo4IQ4MU=",
        'JWT_AUDIENCE': "vlbTest",
        'JWT_ALGORITHM': "HS512",
        'JWT_DURATION': 600  # The following is specified in seconds.
    }
}

GET_STORAGE_DOC_REQ_URL = ("http://localhost:5002/get/{storage_doc_id}")
POST_STORAGE_DOC_REQ_URL = ("http://localhost:5002/add"
                            "?service_key=" + SECURITY["AUTHORISATION_KEY"])
POST_ANNOTATIONS_REQ_URL = ("http://localhost:5001/"
                            "document/{ann_doc_id}/annotations?storageType=2")


MSS = {
    'SWIFT': {
        # shh certificate to connect to remote computer if
        # SWIFT_AUTHENTIFICATION_OPTIONS = V2_REMOTE

        'certificate_filename': 'dir/to/the/certificate.pem',
        # remote computer address if SWIFT_AUTHENTIFICATION_OPTIONS = V2_REMOTE
        'token_server': 'localhost',
        # user if SWIFT_AUTHENTIFICATION_OPTIONS = V2_REMOTE
        'token_server_user': 'user',
        'os-auth-url': 'http://localhost:8080/v2.0',
        'os-tenant-name': 'tenant',
        'os-username': 'username',
        'os-password': 'password',
        'os-region-name': 'region'
        },

    'STORAGE_SERVICE_CONTAINER': 'ServiceStorageMultimedia',

    # Swift token renewal frequency (Twice a day)
    'TOKEN_RENEWAL_FREQ': 43200,

    # Temp URL validity (One day)
    'TEMP_URL_DEFAULT_VALIDITY': 86400,
    # Describes the API used to access swift. The options are V1_LOCAL for
    # Docker local swift, V2 for standard V2 api, and V2_REMOTE when a remote
    # ssh host is used to get swift credentials.
    'SWIFT_AUTHENTIFICATION_OPTIONS': 'V1_LOCAL',
    'SWIFT_REDIRECT_URL': 'http://localhost:8080',
    # Part of the auth url to ignore when returning a swift access url for the
    # client.
    'STORAGE_URL_IGNORE_PREFIX_FOR_TEMP_URL': 'swift'
    }
