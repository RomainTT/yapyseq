#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from collections import namedtuple
from .functiongrabber import FunctionGrabber
from .sequenceanalyzer import SequenceAnalyzer

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Custom types for this module
# ------------------------------------------------------------------------------

ExceptInfo = namedtuple("ExceptInfo", "is_raised name args")
NodeResult = namedtuple("NodeResult", "exception returned")


# ------------------------------------------------------------------------------
# Main class
# ------------------------------------------------------------------------------


class SequenceRunner(object):
    """Class that manages the run of a sequence.

    The aim of an instance of `SequenceRunner` is to run the nodes and manage
    the transitions.

    This object uses a `FunctionGrabber` to access functions that have to be run
    and a `SequenceAnalyzer` to know which function must be executed, and
    determine the order of the nodes.

    `SequenceRunner` has an API to:
        * Initialize the sequence
        * Run the sequence
        * Pause the sequence
        * Stop the sequence
    """

    # --------------------------------------------------------------------------
    # Private methods
    # --------------------------------------------------------------------------

    def __init__(self, func_dir: str, sequence_path: str, variables: dict):
        """Initialize the runner with a given sequence.

        Args:
            func_dir: directory where to search the node functions for.
            sequence_path: path to the sequence file to run.
            variables: sequence variables given for this run.

        Raises:

        """
        # Create basic objects
        self._funcgrab = FunctionGrabber()
        self._seqanal = SequenceAnalyzer(sequence_path)
        self._variables = variables

        # Grab all the functions
        # This is where all the imports can fail
        self._funcgrab.import_functions(func_dir,
                                        self._seqanal.get_all_node_functions())

        # Initialize current nodes
        # The set of nodes that are currently processed
        self._current_nodes = self._seqanal.get_start_node_ids()

    @staticmethod
    def _create_node_result(exception, returned_val) -> NodeResult:
        """Return an easy data structure containing result of a node.

        Args:
            exception: the exception object if the function raised one.
            returned_val: the returned object if the function returned one.

        Returns:
            A nametuple containing all the given data in a structured form.
        """
        if exception:
            except_info = ExceptInfo(True,
                                     type(exception).__name__,
                                     exception.args)
        else:
            except_info = ExceptInfo(False, None, None)

        res = NodeResult(except_info, returned_val)

        return res

    # --------------------------------------------------------------------------
    # Public methods
    # --------------------------------------------------------------------------

    def run(self):
        pass

    def pause(self):
        pass

    def stop(self):
        pass
