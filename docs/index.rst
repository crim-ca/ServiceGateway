Service Gateway documentation
=============================

.. include:: ../README.rst

Infrastructure Overview
-----------------------

This solution relies on the `Celery
<http://celery.readthedocs.org/en/latest/index.html>`_ distributed task queue
and `RabbitMQ <http://www.rabbitmq.com/>`_ messaging broker to dispatch
processing requests. Also, the REST interface uses the `Flask
<http://flask.pocoo.org/>`_ WEB framework.

Basic Usage
-----------

Interface instantiation
+++++++++++++++++++++++

.. note:: Before starting the application, one must apply his own configuration
          values, see :ref:`configuration` section.

For validation purposes, usage is as follows:

.. code-block:: bash

   python run_local.py --help

This command can launch a built-in Flask WEB server. The
«-d» options launches the WEB server in debug mode. Debug mode is useful for
automatic reloading of code and stack trace forwarding. See the Flask
documentation for more information.

.. Warning::

   The REST interface in run_local / debug mode uses a built-in Web Server.
   While this Web Server is useful for a closed environment, it is not
   recommended as a Web Server for a production environment. Care should be
   taken to configure a `WSGI
   <http://wsgi.readthedocs.org/en/latest/index.html>`_ gateway to a
   production-ready WebServer such as `Apache <http://httpd.apache.org/>`_ or
   `GUnicorn <http://gunicorn.org/>`_ behind a reverse-proxy server such as
   NGinx.


Command line client calls
+++++++++++++++++++++++++

.. TODO:: Fold back this information in the Users's guide or at least merge the
          two.

A practical way to interact with the REST API is to use the `curl
<http://curl.haxx.se/>`_ command.

In a new terminal window, issue the following command:

.. code-block:: bash

   curl http://localhost:5000/annotator/annotate\
     --data-urlencode doc_url=http://some.url.wav\
     --data-urlencode ann_doc_id=<ann_doc_id>\
     --header "Authorization: <JWT key>"

Where <JWT key> is a JWT encoded key. For testing purposes a helper script can
be invoked with the following command to generate a valid JWT:

.. code-block:: bash

   python -m VestaRestPackage.jwt_

Or if a :ref:`Multimedia Storage System (MSS)<mss:mss_intro>` is configured
properly in install_config.ini you can use a valid storage_doc_id for document
uploaded to this MSS as follows:

.. code-block:: bash

   curl http://localhost:5000/annotator/annotate/<storage_doc_id>\
       --data-urlencode ann_doc_id=<ann_doc_id> --header "Authorization: <JWT key>"


Where «annotator» would be the name of a given service and «some.url.wav»
indicates the location of a document to process. A uuid would then be returned
and a task request should have been sent on the worker queue where a service
worker could have consumed the request and launched the processing. 

When complete, the annotations will be available through the *status* route.
The *status* route can be invoked as follows:

.. code-block:: bash

   curl http://localhost:5000/annotator/status\?uuid=<UUID>

When invoking the *annotate* route, if the optional ann_doc_id argument is
supplied, the worker will post the annotations on an :ref:`annotation storage
service <jass:jass_home>` for the given annotation document UUID. If an error
occurred when trying to store the annotations, the worker task would have
failed and the annotation process result would be lost.

Furthermore, Celery provides a monitor which can be viewed through a WEB
interface and which also provides a REST API which can be used to monitor and
control tasks. This monitor is named Celery Flower. The use of Flower is
entirely optional at this point but might be included in the run-time
requirements further on. Flower can be started in the following manner:

.. code-block:: bash

   celery flower --config=<config>\
     --broker_api=http://<broker_url>:<broker_port>/api/

Where <broker_url> and <broker_port> should be set to point to the AMQP broker.
<config> is the base name of a Python module providing configuration options to
access the broker. Example contents might be the following:

.. code-block:: python
   
   BROKER_URL = 'amqp://localhost//'
   CELERY_RESULT_BACKEND = 'amqp://'
   CELERY_TASK_SERIALIZER = 'json'
   CELERY_RESULT_SERIALIZER = 'json'
   CELERY_ACCEPT_CONTENT = ['json']
   
Of course <localhost> should be configured to point to the actual broker being
used, which may or may not be the same as the one providing the broker API
specified on the command line above.

See section :any:`celery_config_wrapper` for a helper module if you want to
reuse configuration values for Flower from values extracted from the
application configuration.

Further information on the REST API can be obtained in the documentation's User
Guide.


Vesta Ecosystem
---------------

This package is a central part in the Vesta project developed at CRIM.
Numerous other packages were developed such as:

* Multimedia file Storage System (MSS)
* JSON-LD Annotations Storage System (JASS)
* Numerous annotation services

  * Diarisation Service
  * Speech to text Service
  * Face detection Service
  * etc.

These services were developed with the Service Gateway in mind. Accordingly,
part of the documentation for the Service Gateway applies to the Service
interfaces themselves.

Concerning the MSS and JASS, it is not required that these be installed
alongside the Service Gateway yet they offer useful functionalities and some
exposed services might require them. 

Below is an illustration of the many relationships between the elements of the
Vesta Services ecosystem.

.. image:: vesta_ecosystem.png
   :width: 800px


User's Guide
------------

Describes the typical usage of the Service Gateway REST API functions.

.. toctree::
   :maxdepth: 3

   user_guide


Package information
-------------------

.. toctree::
   :maxdepth: 2

   install
   authors
   license
   provenance
   source
   release_notes


Source code documentation
-------------------------

This section documents the actual code modules for anyone interested in
interfacing with the code base or to study the code internals.


Code structure
++++++++++++++

- Shared interface between MSS and Service Gateway
- Common software package shared between MSS/Service Gateway and worker
  services, speeding up the development of new worker services.

  - Defines message format and contents along with processing methodology


Package level
+++++++++++++

.. toctree::
   :maxdepth: 2
   :glob:

   src/*


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
