.. _readme:

NEP-143-2 Service Gateway
=========================

This package offers a HTTP REST API to a distributed service queue Service
Gateway (SG). 

Overview
--------

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
  * Passes arbitrary arguments onwards to the selected worker.

* Provide an asynchronous API to query the advancement of long duration
  tasks.

  * Exposes methods to communicate progress [0-100] to the REST front-end.

* Provides methods to evaluate infrastructure needs.

The documentation for this project can be found `here
<http://vesta.crim.ca/docs/sg/latest/>`_ .