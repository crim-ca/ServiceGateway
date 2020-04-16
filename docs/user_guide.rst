... _common_rest_interface:

Service Gateway interface documentation
=======================================


Purpose
-------

The Service Gateway is essentially a Gateway from an HTTP REST interface to Celery/AMQP interface.

This document describes the WEB service interfaces that are common for each service which can be exposed by the current Service Gateway.

It shows how a service can be used, the standard response types and how to handle exceptions.


Methods
-------

Most methods are supplied my an underlying package which offers base methods to control Service workers, including the basic routes required by the CANARIE Service API.

The Service Gateway builds on top of these methods and offers more specific functionalities.

See :ref:`Rest interface overview <vrp:user_guide_overview>` for general information on the REST interface. All of the functions provided by the common REST interface are also available in this element.


.. _lb_methods:

The Service Gateway REST interface is used to launch and monitor an annotation processing request for a given document using any of the supported annotator services.

It covers:

* <Base URI>/annotate
* <Base URI>/process
* <Base URI>/status
* <Base URI>/cancel
* /service_workflow/process

Where <Base URI> will look like <Server>/<annotator_name>. e.g.::

   http://vesta.crim.ca/diarisation

The specific service documentation should be checked to have an overview of supported services.


.. _annotate_method:

annotate
~~~~~~~~

Launch the processing for a given document. Optionally store resulting annotations on a remote :ref:`Annotations Storage Service <jass:jass_home>` when supplying annotation document UUID.

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

Any additional parameters which are passed at request time that do not correspond to the parameter names above are forwarded to the annotation worker through a data structure with the "misc" key. The key value pair names are kept. This enables a developer to use arbitrary argument names in the HTTP request that will be forwarded to a given service through the JSON data structure communicated across AMQP/Celery.

Return value:

The service returns a JSON structure containing an «uuid» identifying the processing request:

.. code-block:: json

   {
       "uuid": "6547137e-cc2f-4008-b1eb-4ae8e898ce83"
   }

The resulting «uuid» can then be used to perform further status queries to the service.

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


process
~~~~~~~

This method is essentially the same as :ref:`annotate_method` with the following difference: this method accepts a JSON structure containing arbitraty arguments as http POST body contents. The whole structure is passed on to the service in the misc dictionnary.

The URL parameters which are required in the :ref:`annotate_method` are required as well for the process method. Hence one can submit a request in the same manner as for the annotate method yet also supply JSON contents in the body.

For example:

.. code-block:: bash

   curl -X POST --data-urlencode ann_doc_id=541a0ebb1747d5305901b48a\
      <Base URI>/process --data-urlencode doc_url=http://localhost:8000/short_en.wav\
      --data-binary "@path/to/file"

In which the file contents would be for example:

.. code-block:: json

   {
       "task": "VideoOnly",
       "videoparams": {
           "codec": "h264",
           "bitrate": "1000k"
       },
       "dest": {
           "url": "ftp://ftp.server.ca/dest/tmp",
           "username": "myuser",
           "password": "my_password"
       }
   }


status
~~~~~~

To obtain the status or results of a given processing request

This method uses HTTP GET.


Parameters:

:uuid: The identifier of a previous processing request.


Return value:

Returns a given response depending on the processing state. Consult the :ref:`status_method` page for the documentation of the response format.


Examples:

URL form:

.. code-block:: bash

   <Base URI>/status?uuid=6547137e-cc2f-4008-b1eb-4ae8e898ce83


.. Security ------------------------------------------------------

The Service Gateway can use authorization tokens to protect it's routes from unwanted access. This is done with the use of `JWT <https://jwt.io/>`_ according to the deployment :ref:`default_config_values`.

service_workflow/process
~~~~~~~~~~~~~~~~~~~~~~~~
This method allows to make a single call containing all the information required to use multiple services at once.
All files and parameters are supplied at call. All the files supplied are used temporarerly, and will be erased.

The POST method should contain all required and a 'json' field containing a json off all parameters required to execute the service.
For example:

.. code-block:: bash

   curl -X POST -F 'file1=@/home/centos/short_en.wav' \ -F 'json=<supplied json>'
      <SG URI>/simple_workflow/process

.. code-block:: json

    {
       "services":[{
          "service_name":"transcoding",
          "url":"file1",
          "dest":{
             "yolo":"s__1.wav__e"
          },
          "audioparams":{
             "bitrate":"128k",
             "channels":"1"
          },
          "format":"wav",
          "task":"AudioOnly"
       },
       {
          "service_name":"diarisation",
          "url":"s__1.wav__e",
          "win_size":250,
          "thr_l":2,
          "thr_h":7,
          "thr_vit":-250,
          "vad_params":{
             "apply_vad":true,
             "intersil":6,
             "mindur":50
          }
       }]
    }

:services: (required array): Contains parameters necessary to execute the service.
Each entry in the list corresponds to a service. Each service should have a field serviceName, indicating the name of the service as used in :ref:`annotate_method`.
All services requiring a file will have a "url" parameter for input file.
When chaining services, often destination of one can be used as url to then next one. The result of the last service is returned. In the case a temporary storage is
used for intermediary results, it is possible to use the following format : **s__<number/GUID><.optional extension>__e** will generate a temporary url for the resulting file.
This parameter can be reused to refer to this file during execution. The **file1** in the transcoding url part, will be replaced by the supplied file /home/centos/short_en.wav. All file form names, will be replaced automatically
by corresponding file, by storing the files as temporary URLs.