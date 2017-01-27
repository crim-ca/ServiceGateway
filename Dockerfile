FROM centos:centos7

# Install required libraries -------------------------------
RUN yum install -y \
    python2-devel \
    gcc \
    wget \
    git \
    tar

RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python ./get-pip.py

# Install external dependencies -------------------
RUN pip install python-swiftclient \
                python-keystoneclient \
                gunicorn \
                nose

# Application -------------------------------------
COPY . /var/local/src/ServiceGateway

RUN pip install \
        git+https://github.com/crim-ca/RESTPackage.git@worker_natural_naming \
        /var/local/src/ServiceGateway

EXPOSE 5000

RUN nosetests -v ServiceGateway

CMD gunicorn -w 4 -preload -b 0.0.0.0:5000 ServiceGateway.rest_api:APP --log-config=/var/local/src/ServiceGateway/ServiceGateway/logging.ini
