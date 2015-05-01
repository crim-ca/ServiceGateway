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

from VestaLoadBalancer.__meta__ import __version__, __author__, __contact__

REQUIREMENTS = ["Flask==0.10.1",
                "Sphinx==1.2.2",
                "Werkzeug==0.9.4",
                "celery==3.1.15",
                "requests==2.6",
                "pyrabbit==1.0.1",
                "PyJWT==0.4.3",
                "python-novaclient"]

setup(
    # -- Meta information --------------------------------------------------
    name='VestaLoadBalancer',
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
    packages=['VestaLoadBalancer',
              'VestaLoadBalancer.VestaRestPackage',
              'VestaLoadBalancer.VestaRestPackage.Service'],

    install_requires=REQUIREMENTS,
    zip_safe=False,

    exclude_package_data={'VestaLoadBalancer': ['.hg', '.hglf']},

    package_data={
        'VestaLoadBalancer': ['static/*', 'templates/service/*'],
        'VestaLoadBalancer.VestaRestPackage':
            ['static/*', 'templates/*', 'test_data/*'],
        },

    entry_points={
        'console_scripts':
            ['vlb_default_config='
             'VestaLoadBalancer.VestaRestPackage.'
             'print_example_configuration:main',
             'rubber=VestaLoadBalancer.rubber:main']}
    )
