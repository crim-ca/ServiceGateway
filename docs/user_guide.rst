.. _common_rest_interface:

Service Gateway interface documentation
=======================================


Purpose
-------

The Service Gateway is essentially a Gateway from an HTTP REST interface to
Celery/AMQP interface.

This document describes the WEB service interfaces that are common for each
service which can be exposed by the current Service Gateway.

It shows how a service can be used, the standard response types
and how to handle exceptions.


.. overview ---------------------------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_overview.rst


Methods
-------

Most methods are supplied my an underlying package which offers base methods to
control Service workers, including the basic routes required by the CANARIE
Service API.

The Service Gateway builds on top of these methods and offers more
specific functionalities. 


.. _lb_methods:

Service Gateway methods set
+++++++++++++++++++++++++++

The Service Gateway REST interface is used to launch and monitor an annotation
processing request for a given document using any of the supported annotator
services. 

It covers:

* <Base URI>/annotate
* <Base URI>/status
* <Base URI>/cancel

Where <Base URI> will look like <Server>/<annotator_name>. e.g.::

   http://vesta.crim.ca/diarisation

The specific service documentation should be checked to have an overview of
supported services.


.. _annotate_method:

annotate
~~~~~~~~

Launch the processing for a given document. Optionally store resulting
annotations on a remote :ref:`Annotations Storage Service <jass:jass_home>`
when supplying annotation document UUID.

This method uses HTTP POST.

Parameters:

:storage_doc_id: Storage document id given by the :ref:`Multimedia Storage
   Service <mss:mss_home>`.
:doc_url: [Optional] URL of document to be processed (Can be used in
   replacement of the storage_doc_id).
:ann_doc_id: [Optional] argument giving Annotations Storage Service
   :ref:`document ID <jass:create_document>` to which the annotations will be
   appended. If the user omits this variable the annotator will not call any
   Annotations Storage Service but will log a Warning message with information
   regarding this fact.

Any additional parameters which are passed at request time that do not
correspond to the parameter names above are forwarded to the annotation worker
through a data structure with the "misc" key. The key value pair names are
kept. This enables a developer to use arbitrary argument names in the HTTP
request that will be forwarded to a given service through the JSON data
structure communicated across AMQP/Celery.

Return value:

The service returns a JSON structure containing an «uuid» identifying the
processing request:

.. code-block:: json

   {
       "uuid": "6547137e-cc2f-4008-b1eb-4ae8e898ce83"
   }

The resulting «uuid» can then be used to perform further status queries to the
service.

.. note:: If there is a need to use an Annotations Storage Service as a back-end
          the configuration of the LoadBalancer must specify the Annotations
          Storage Service storage URL to which the annotations will be appended
          via a HTTP POST call. See :ref:`configuration` section.


Examples:

URL form:

.. code-block:: bash

   <Base URI>/annotate/5hEK1ToPWHVhE3Irje5KRq.mp4?ann_doc_id=541a0ebb1747d5305901b48a


Alternatively::

   <Base URI>/annotate?doc_url=http://localhost:8000/short_en.wav


With the curl utility:

.. code-block:: bash

   curl -X POST --data-urlencode ann_doc_id=541a0ebb1747d5305901b48a\
       <Base URI>/annotate/5hEK1ToPWHVhE3Irje5KRq.mp4


Alternatively:

.. code-block:: bash

   curl -X POST --data-urlencode ann_doc_id=541a0ebb1747d5305901b48a\
      <Base URI>/annotate --data-urlencode doc_url=http://localhost:8000/short_en.wav


status
~~~~~~

To obtain the status or results of a given processing request

This method uses HTTP GET.


Parameters:

:uuid: The identifier of a previous processing request.


Return value:

Returns a given response depending on the processing state. Consult the
:ref:`status_method` page for the documentation of the response format.


Examples:

URL form:

.. code-block:: bash

   <Base URI>/status?uuid=6547137e-cc2f-4008-b1eb-4ae8e898ce83



.. cancel method -------------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_cancel_method.rst


.. Info route ----------------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_info_route.rst


.. Status method -------------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_status_method.rst


.. CANARIE API ---------------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_canarie_api.rst


.. Error codes section ===========================================
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_error_codes_preamble.rst


.. Core error codes ----------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_core_error_codes.rst


.. VRP error codes -----------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_vrp_error_codes.rst


.. Service error codes -------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_worker_services_error_codes.rst


.. Vision error codes --------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_vision_error_codes.rst


.. Speech error codes --------------------------------------------
.. include:: ../ServiceGateway/VestaRestPackage/docs/ug_speech_error_codes.rst