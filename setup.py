#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setuptools configuration script.
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.rst') as readme_file:
    README = readme_file.read()
    DESC = README.split('\n')[0]

with open('HISTORY.rst') as history_file:
    HISTORY = history_file.read().replace('.. :changelog:', '')

from ServiceGateway.__meta__ import __version__, __author__, __contact__

REQUIREMENTS = ["Flask==0.10.1",
                "Sphinx==1.3.1",
                "celery==3.1.19",
                "requests==2.8.1",
                "pyrabbit==1.0.1",
                "PyJWT==0.4.3",
                "dicttoxml==1.6.6",
                "python-novaclient==2.23.0"]

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
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],

    # -- Package structure -------------------------------------------------
    packages=['ServiceGateway',
              'ServiceGateway.VestaRestPackage'],

    install_requires=REQUIREMENTS,
    zip_safe=False,

    exclude_package_data={'ServiceGateway': ['.hg', '.hglf']},

    package_data={
        'ServiceGateway': ['static/*', 'templates/service/*'],
        'ServiceGateway.VestaRestPackage':
            ['static/*', 'templates/*', 'test_data/*'],
        },

    entry_points={
        'console_scripts':
            ['vlb_default_config='
             'ServiceGateway.VestaRestPackage.'
             'print_example_configuration:main',
             'rubber=ServiceGateway.rubber:main']}
    )
