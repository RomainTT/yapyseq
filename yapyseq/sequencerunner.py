#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from collections import namedtuple
from typing import Callable, Dict
import multiprocessing as mp
from enum import Enum

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


class SeqRunnerStatus(Enum):
    RUNNING = 0
    PAUSING = 1
    PAUSED = 2
    STOPPING = 3
    STOPPED = 4
    INITIALIZED = 5

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
            Exceptions from SequenceAnalyzer and FunctionGrabber.
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

        # Update status
        self.status = SeqRunnerStatus.INITIALIZED

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

    @staticmethod
    def _run_node_function(func: Callable, semaphore: mp.Semaphore, result_queue: mp.Queue,
                           args: Dict = None, timeout: int = None) -> None:
        """Function that can be called in a thread to run a node function and share its result.

        This function must:
          * Run the given callable that has been given, with the given arguments
          * Manage a Timeout on this callable
          * Provide the result of the callable through a Queue
          * Notify the end of itself using a semaphore

        Args:
            func: The function to be run. Must be a callable.
            semaphore: The semaphore that must be released when _run_node_function() is over.
            result_queue: The Queue object to store the result of the node function.
              The stored object will be of type NodeResult.
            args: (optional) The arguments to give to the function.
            timeout: (optional) The time limit for the function to be terminated.
        """

        # TODO: manage timeout

        # Run the callable
        try:
            func_res = func(**args)
        except Exception as e:
            res = SequenceRunner._create_node_result(e, None)
        else:
            res = SequenceRunner._create_node_result(None, func_res)

        # Provide result through the Queue
        result_queue.put(res)

        # End of _run_node_function(),
        # release the semaphore to notify the end of one node.
        semaphore.release()

    # --------------------------------------------------------------------------
    # Public methods
    # --------------------------------------------------------------------------

    def run(self, blocking: bool = True):
        """Run the sequence.

        Args:
            blocking: (optional) Set to True to make the run() method as
              blocking, meaning it won't return until there is no more nodes
              to run. If set to False, the runner will be launched in a new
              thread. This is useful if one wants to be able to call pause()
              and stop() while the sequence is running.
              TODO: implement the non blocking feature

        Raises:

        """
        self.status = SeqRunnerStatus.RUNNING

    def pause(self):
        self.status = SeqRunnerStatus.PAUSING
        # Some code...
        self.status = SeqRunnerStatus.PAUSED

    def stop(self):
        self.status = SeqRunnerStatus.STOPPING
        # Some code
        self.status = SeqRunnerStatus.STOPPED
