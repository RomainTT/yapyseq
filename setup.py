#!/usr/bin/env python
# encoding: utf-8

from setuptools import setup, find_packages

setup(name='yapyseq',
      version='0.1',
      description='Yet Another Python Sequencer',
      author='Romain TAPREST',
      author_email='romain@taprest.fr',
      url='',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['pyyaml', 'yamale', 'Click'],
      tests_require=['pytest'],
      entry_points='''
          [console_scripts]
          yapyseq=yapyseq.cli:yapyseq_main_cli
      '''
      )
