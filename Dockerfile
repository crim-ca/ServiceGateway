FROM centos:6.6

# Install required libraries -------------------------------
RUN rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
RUN yum install -y \
    hg \
    python2-devel \
    gcc \
    python-pip \
    wget \
    tar

# Libabries missing from the base CentOS install ---------------
RUN mkdir -p /tmp/install/netifaces/

RUN cd /tmp/install/netifaces &&\
    wget -O "netifaces-0.10.4.tar.gz"\
        "https://pypi.python.org/packages/source/n/netifaces/netifaces-0.10.4.tar.gz#md5=36da76e2cfadd24cc7510c2c0012eb1e"

RUN cd /tmp/install/netifaces/ &&\
    tar xvzf netifaces-0.10.4.tar.gz

RUN cd /tmp/install/netifaces/netifaces-0.10.4 &&\
    python setup.py install

# Install external dependencies -------------------
RUN pip install python-swiftclient \ 
                python-keystoneclient \
                gunicorn

# Application -------------------------------------

RUN pip install git@github.com:crim-ca/ServiceGateway.git

ENV VRP_CONFIGURATION /opt/vlb/config.py

RUN mkdir -p /opt/vlb

EXPOSE 5000

WORKDIR /opt/vlb

CMD gunicorn -w 4 -preload -b 0.0.0.0:5000 ServiceGateway.rest_api:APP --log-config=logging.conf
