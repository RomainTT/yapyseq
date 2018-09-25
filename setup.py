#!/usr/bin/env python
# encoding: utf-8

from setuptools import setup

setup(name='yapyseq',
      version='0.1',
      description='Yet Another Python Sequencer',
      author='Romain TAPREST',
      author_email='romain@taprest.fr',
      url='',
      packages=['yapyseq'],
      install_requires=['pyyaml', 'yamale'],
      tests_require=['pytest']
      )
