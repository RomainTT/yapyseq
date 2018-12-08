#!/usr/bin/env python
# encoding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
from setuptools import setup, find_packages


def get_long_description():
    """Return readme description"""
    with open('README.md') as fp:
        return fp.read()


def get_version():
    """Return the version of the package"""
    with open(os.path.join('.', 'VERSION')) as fp:
        return fp.read().strip()


setup(
    name='yapyseq',
    version=get_version(),
    description='Yet Another Python Sequencer',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='Romain TAPREST',
    author_email='romain@taprest.fr',
    url='https://github.com/RomainTT/yapyseq',
    packages=find_packages(),
    package_data={'yapyseq': ['seq_schema.yaml']},
    data_files=[('.', ['VERSION'])],
    install_requires=['ruamel.yaml', 'yamale', 'click'],
    tests_require=['pytest'],
    license="MPL-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: OS Independent",
    ],
    entry_points='''
        [console_scripts]
        yapyseq=yapyseq.cli:yapyseq_main_cli
    '''
)
