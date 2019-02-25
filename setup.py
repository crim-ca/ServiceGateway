#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setuptools configuration script.
"""

from ServiceGateway.__meta__ import __version__, __author__, __contact__

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.rst') as readme_file:
    README = readme_file.read()
    DESC = README.split('\n')[0]

with open('HISTORY.rst') as history_file:
    HISTORY = history_file.read().replace('.. :changelog:', '')

REQUIREMENTS = ["python-novaclient==2.23.2",
                "VestaRestPackage==1.9.0"]

setup(
    # -- Meta information --------------------------------------------------
    name='ServiceGateway',
    version=__version__,
    description=DESC,
    long_description=README + '\n\n' + HISTORY,
    author=__author__,
    author_email=__contact__,
    url='http://www.crim.ca',
    license="copyright CRIM 2015",
    platforms=['linux-x86_64'],
    keywords='CANARIE, LoadBalancing, Services',
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],

    # -- Package structure -------------------------------------------------
    packages=['ServiceGateway'],

    install_requires=REQUIREMENTS,
    zip_safe=False,

    package_data={'ServiceGateway': ['static/*', 'templates/service/*']},

    entry_points={'console_scripts': ['rubber=ServiceGateway.rubber:main']}
    )
