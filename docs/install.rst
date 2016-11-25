.. include:: ../INSTALL.rst

Docker Builds
=============

This interface has been containerized and you can also create your own images
by using the following Dockerfile contents:

.. note:: The following Dockerfile implies that you have a copy of the source
          code and that you are executing the *docker build* command from the
          top level of the package structure.

.. literalinclude:: ../Dockerfile
   :linenos:
   :language: docker
