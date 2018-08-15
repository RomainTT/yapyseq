#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


class SequenceAnalyzer(object):
    """Class that can read and analyze a sequence description file.

    The aim of an instance of `SequenceAnalyzer` is to read a `.yaml` file that
    describes a sequence, and analyze it to be able to provide useful
    information through its API.

    Provided useful information can be, for instance:
    * The name of the sequence.
    * The number of nodes.
    * The name of the function to be executed in a particular node.
    * The following node to be executed, knowing the source node and some
      variables used for decision making.
    """
    def __init__(self):
        pass
