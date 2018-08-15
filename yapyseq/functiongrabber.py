#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from types import FunctionType


class FunctionGrabber(object):
    """Class to get access to functions of a specific directory.

    The aim of an instance of `FunctionGrabber` is:
        * to import the python files containing the functions that can be
          executed in a given sequence.
        * Provide these functions on demand through its API
    """
    def __init__(self, directory: str):
        pass

    def import_functions(self, sequence):
        pass

    def get_function(self, func_name: str) -> FunctionType:
        pass
