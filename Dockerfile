FROM centos:centos7

# Install required libraries -------------------------------
RUN yum install -y \
    python2-devel \
    gcc \
    wget \
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

RUN pip install /var/local/src/ServiceGateway

EXPOSE 5000

RUN nosetests -v ServiceGateway

ENTRYPOINT gunicorn ServiceGateway.rest_api:APP

CMD -w 4 -preload -b 0.0.0.0:5000 --log-config=/var/local/src/ServiceGateway/ServiceGateway/logging.ini
