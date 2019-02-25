.. :changelog:

History
=======

1.8.4
-----

* Updated VestaRestPackage to 1.9.1 with MonboDB support.

1.8.3
-----

* Fix handling of worker exceptions encoded in UTF-8.

1.8.2
-----

* Configuration directive no_params_needed is now optionnal.

1.8.1
-----

* Fix handling of case where JSON is submitted and no_params_needed = False.

1.8.0
-----

* Can use a JSON body subitted to the process route.
* Configuration for a service can contain a no_parameter directive.
* Fixes to error handling for certain types of exceptions.  

1.7.6
-----

* Can use a task name a number of times on different queues.

1.7.3
-----

* Fix version declaration when called by WSGI.

1.7.2
-----

* Fix bug in arbitrary parameter use.

1.7.0
-----

* Arbitrary arguments which are unknown are passed onwards to the worker through the "misc" sub-structure in JSON.

1.6.0
-----

* First packaged release
* Deployment configuration factored out of package


1.5.5
-----

* HTTP Authorization mechanism with JWT sent through HEADER on annotation requests.
* Redirect to documentation pages which are to be statically hosted elsewhere
* Can handle extra document specification in URL arguments (\*_url or storage\_\*_id)


1.5.4
-----

* Add a ./service/. route to reflect CANARIE API requirements.


1.5.3
-----

* Use a version of transition 1.1.0 and faceanalysis 1.0.0 services that
    conform to the JSON-lD scheme.

1.5.0
-----

* Error handling is completed
* Uniform error codes
* More logs
* Normalise some fields in the result structure

1.4.0
-----

* Support of storage_doc_id replacing the full URL 
* Queue will expires in 2 hours by default: Add a Status of EXPIRED when a queue is no longer available
* Complete the annotations storage for a given ann_doc_id
* Task UUIDs are stored using a method that supports concurrency

1.3.0
-----

* Support ann_doc_id argument.
* New versioning scheme.

1.1.0
-----

* Add a cancel function to stop a running task.
