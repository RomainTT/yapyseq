#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


class SequenceRunner(object):
    """Class that manages the run of a sequence.

    The aim of an instance of `SequenceRunner` is to travel across the nodes
    of the sequence in the right order, executing each function of each node
    it passes through.

    This object uses a `FunctionGrabber` to access functions that have to be run,
    and a `SequenceAnalyzer` to know in which order the nodes must be executed.

    `SequenceRunner` has an API to:
        * Initialize the sequence
        * Run the sequence
        * Pause the sequence
        * Stop the sequence
    """
    def __init__(self):
        pass

    def initialize(self):
        pass

    def run(self):
        pass

    def pause(self):
        pass

    def stop(self):
        pass
