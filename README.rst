===================================================
NEP-143-2 SG (Service Gateway)
===================================================

This package offers a simple load balancer residing behind a REST API. 

It's intended use is for the exploitation of services on the CANARIE network
whose services are CPU intensive and which would benefit from a dynamic
horizontal scaling approach to provide reasonable processing delays for the
REST client and better reactivity of the interface itself.

The different functions offered by this code base are the following: 

 * Provide a unified CANARIE REST interface for a collection of given services
   on a given infrastructure.

 * Provide a gateway to a queue-based distributed processing framework based on
   AMQP and Celery

   * A collection of utilities to aid in adding new worker types to the
     processing queues.
   * Implements a standard messaging scheme for workers / controller.

 * Provide an asynchronous API to query the advancement of long duration
   tasks.

   * Exposes methods to communicate progress [0-100] to the REST front-end.

 * Provides methods to evaluate infrastructure needs.

This solution relies on the `Celery
<http://celery.readthedocs.org/en/latest/index.html>`_ distributed task queue
and `RabbitMQ <http://www.rabbitmq.com/>`_ messaging broker to dispatch
processing requests. Also, the REST interface uses the `Flask
<http://flask.pocoo.org/>`_ WEB framework.

-------
LICENSE
-------

see https://github.com/crim-ca/ServiceGateway/tree/master/THIRD-PARTY-LICENSES.rst

------------
Installation
------------

You can use the `pip
<https://pip.readthedocs.org/en/latest/reference/pip_install.html>`_ utility to
install this package. One way of doing that is by pointing pip directly to the
directory containing the setup.py file such as::

   pip install .

This will install the VestaLoadBalancer along with program entry points for
various utilities.

A good practise might be to make use of a `virtual environment
<https://virtualenv.pypa.io/en/latest/>`_ in which all the
dependencies will be installed through pip. 

Tests were conducted on Python 2.6.x and should normally worker under version
2.7 (untested).

Usage
-----

For validation purposes, usage is as follows::

   python run_local.py --help

This command can launch a built-in Flask WEB server. The
«-d» options launches the WEB server in debug mode. Debug mode is useful for
automatic reloading of code and stack trace forwarding. See the Flask
documentation for more information.

.. warning::

   The REST interface in run_local / debug mode uses a built-in Web Server. While
   this Web Server is useful for a closed environment, it is not recommended as a
   Web Server for a production environment. Care should be taken to configure a
   `WSGI <http://wsgi.readthedocs.org/en/latest/index.html>`_ gateway to a
   production-ready WebServer such as `Apache <http://httpd.apache.org/>`_ or
   `GUnicorn <http://gunicorn.org/>`_ behind a reverse-proxy server such as
   NGinx.

On another terminal still::

   curl http://localhost:5000/annotator/annotate --data-urlencode doc_url=http://some.url.wav --data-urlencode ann_doc_id=<ann_doc_id> --header "Authorization: <JWT key>"

Where <JWT key> is a JWT encoded key. For testing purposes a helper script can
be invoked with the following command to generate a valid JWT::

    python -m VestaRestPackage.jwt_

Or if the MSS is configured properly in install_config.ini you can use a valid
storage_doc_id for document uploaded to this MSS as follows::

   curl http://localhost:5000/annotator/annotate/<storage_doc_id> --data-urlencode ann_doc_id=<ann_doc_id> --header "Authorization: <JWT key>"


Where «annotator» would be the name of a given service and «some.url.wav»
indicates the location of a document to process. A uuid would then be returned
and a task request should have been sent on the worker queue where a service
worker could have consumed the request and launched the processing. 

When complete, the annotations will be available through the status route. See
documentation.

If the optional ann_doc_id argument is supplied, the worker will post the
annotations on an annotation storage service for the given annotation document
UUID. If an error occurred when trying to store the annotations, the worker task
would have failed and the annotation process result would be lost.

Furthermore, Celery provides a monitor which can be viewed through a WEB
interface and which also provides a REST API which can be used to monitor and
control tasks. This monitor is named Celery Flower. The use of Flower is
entirely optional at this point but might be included in the run-time
requirements further on. Flower can be started in the following manner::

   celery flower --config=<config> --broker_api=http://<broker_url>:<broker_port>/api/

Where <broker_url> and <broker_port> should be set to point to the AMQP broker.
<config> is the base name of a Python module providing configuration options to
access the broker. Example contents might be the following::

   
   BROKER_URL = 'amqp://localhost//'
   CELERY_RESULT_BACKEND = 'amqp://'
   CELERY_TASK_SERIALIZER = 'json'
   CELERY_RESULT_SERIALIZER = 'json'
   CELERY_ACCEPT_CONTENT = ['json']
   
Of course <localhost> should be configured to point to the actual broker being
used, which may or may not be the same as the one providing the broker API
specified on the command line above.
