#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from collections import namedtuple
from typing import Callable, Dict, Set, Union, Any
import multiprocessing as mp
from queue import Empty as EmptyQueueException
from enum import Enum

from yapyseq.functiongrabber import FunctionGrabber
from yapyseq.sequencereader import SequenceReader
from yapyseq.nodes import FunctionNode, StartNode, StopNode, VariableNode, \
    ParallelSyncNode, ParallelSplitNode

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class UnknownNodeTypeError(ValueError):
    pass


class NodeFunctionTimeout(TimeoutError):
    pass


class ReadOnlyError(ValueError):
    pass

# ------------------------------------------------------------------------------
# Custom types for this module
# ------------------------------------------------------------------------------


ExceptInfo = namedtuple("ExceptInfo", "is_raised name args")
FunctionNodeResult = namedtuple("FunctionNodeResult", "nid exception returned")


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

    Attributes:
        status:
    """

    # --------------------------------------------------------------------------
    # Private methods
    # --------------------------------------------------------------------------

    def __init__(self, func_dir: str, sequence_path: str, constants: dict):
        """Initialize the runner with a given sequence.

        Args:
            func_dir: directory where to search the node functions for.
            sequence_path: path to the sequence file to run.
            constants: sequence constants given for this run.

        Raises:
            Exceptions from SequenceAnalyzer and FunctionGrabber.
        """
        # Create basic objects
        self._funcgrab = FunctionGrabber()
        self._seqreader = SequenceReader(sequence_path)

        # Define the set of variables that are read-only
        # There are yapyseq built-in variables, sequence constants,
        # and given constants
        self._read_only_var = {'results'}
        self._read_only_var.update(self._seqreader.get_constants())
        self._read_only_var.update(constants.keys())

        # Initialize the dictionary of variables.
        # It contains both read-only and writeable variables
        self._variables = dict()
        self._variables.update(constants)
        self._variables.update(self._seqreader.get_constants())
        # Add an empty dict of results in the variables
        # It will be filled with node results while the sequence is running.
        self._variables['results'] = dict()

        # See SequenceRunner.run() for the uses of the following attribute.
        self._result_queue = mp.Queue()

        # Grab all the functions
        # This is where all the imports can fail
        self._funcgrab.import_functions(
            func_dir,
            self._seqreader.get_node_function_names())

        # Get the dictionary of nodes
        # keys are the nids, and values the node objects
        self._nodes = self._seqreader.get_node_dict()

        # Initialize new_nodes as a set of objects of type NewNode.
        # At first, new nodes are the start nodes of the sequence.
        self._new_nodes = set()
        start_nid = self._seqreader.get_start_node_ids()
        self._add_new_nodes(start_nid, None)  # previous nodes are None

        # Initialize running_nodes
        # A dictionary of nodes that are currently running
        # Node ids are keys, and their processes are values
        self._running_nodes: Dict[int, mp.Process] = dict()

        # Update status
        self.status = SeqRunnerStatus.INITIALIZED

    @staticmethod
    def _create_node_result(node_id: int, exception: Union[None, Exception],
                            returned_obj: Any) -> FunctionNodeResult:
        """Return an easy data structure containing result of a node.

        Args:
            exception: the exception object if the function raised one.
            returned_obj: the returned object if the function returned one.

        Returns:
            A nametuple containing all the given data in a structured form.
        """
        if exception:
            except_info = ExceptInfo(True,
                                     type(exception).__name__,
                                     exception.args)
        else:
            except_info = ExceptInfo(False, None, None)

        res = FunctionNodeResult(node_id, except_info, returned_obj)

        return res

    @staticmethod
    def _run_node_function_no_timeout(func: Callable, node_id: int,
                                      result_queue: mp.Queue,
                                      kwargs: Dict = None) -> None:
        """Function that can be called in a thread to run a node function.

        This function must:
          * Run the given callable that has been given, with the given arguments
          * Provide the result of the callable through a Queue

        Args:
            func: The function to be run. Must be a callable.
            node_id: The ID of the node containing the function. It is only used
              to be stored in the result object.
            result_queue: The Queue object to store the result of the node
              function. The stored object will be of type FunctionNodeResult.
            kwargs: (optional) The arguments to give to the function.
        """

        # Run the callable
        try:
            func_res = func(**kwargs)
        except Exception as e:
            res = SequenceRunner._create_node_result(node_id, e, None)
        else:
            res = SequenceRunner._create_node_result(node_id, None, func_res)

        # Provide result through the Queue
        result_queue.put(res)

    @staticmethod
    def _run_node_function_with_timeout(func: Callable, node_id: int,
                                        result_queue: mp.Queue,
                                        kwargs: Dict = None,
                                        timeout: int = None) -> None:
        """Function that can be called in a thread to run a node function.

        This function must:
          * Run the given callable that has been given, with the given arguments
          * Manage a Timeout on this callable
          * Provide the result of the callable through a Queue

        Args:
            func: The function to be run. Must be a callable.
            node_id: The ID of the node containing the function. It is only used
              to be stored in the result object.
            result_queue: The Queue object to store the result of the node
              function. The stored object will be of type FunctionNodeResult.
            kwargs: (optional) The arguments to give to the function.
            timeout: (optional) The time limit for the function to be
              terminated.
        """
        if not timeout:
            # Just start the function without timeout
            # and without creating a new thread.
            # Note: this separate condition could be avoided because Queue.get
            # manages a None timeout, but this implementation avoids creating
            # unnecessary sub-threads, so it is better like this !
            SequenceRunner._run_node_function_no_timeout(
                func, node_id, result_queue, kwargs)
        else:
            # Create a sub-result queue for the real run of the function
            sub_result_queue = mp.Queue()
            # Start the function in the new sub-thread
            process = mp.Process(
                target=SequenceRunner._run_node_function_no_timeout,
                name="Node {} sub-thread".format(node_id),
                kwargs={'func': func,
                        'node_id': node_id,
                        'result_queue': sub_result_queue,
                        'kwargs': kwargs})
            process.start()
            result = None  # Just in case something goes wrong in try except
            try:
                # Wait until result or timeout
                result = sub_result_queue.get(block=True, timeout=timeout)
            except EmptyQueueException:
                # timeout occurred !
                # Create a timeout exception to put in the result
                exception = NodeFunctionTimeout(
                    "Function {} of node {} timed out !".format(func.__name__,
                                                                node_id))
                result = SequenceRunner._create_node_result(
                    node_id, exception, None)
            finally:
                # Put the final result in the result queue
                result_queue.put(result)

    def _add_new_nodes(self, new_node_ids: Union[int, Set[int]],
                       previous_node_id: Union[int, None]) -> None:
        """Add one or several new nodes to self._new_nodes.

        Warning:
            This method should only be used in the run() function of this class,
            or during initialization in __init__().
            It modifies the internal state of the SequenceRunner object.

        Args:
            new_node_ids: The ID or a set of IDs of the new nodes to add.
            previous_node_id: the ID of the previous node of the new one.
        """
        # Transform the argument into a set if it is not
        if type(new_node_ids) is not set:
            new_node_ids = {new_node_ids}

        for new_node_id in new_node_ids:
            # Get the corresponding node object
            new_node = self._nodes[new_node_id]
            # Update the previous node of this node
            new_node.previous_node_id = previous_node_id
            # Add this node object to the set of new nodes
            self._new_nodes.add(new_node)

    def _manage_new_node(self, new_node) -> None:
        """Manage a new node in the running sequence.

        Warning:
            This method should only be used in the run() function of this class.
            It modifies the internal state of the SequenceRunner object.

        Args:
            new_node: the node object to process.

        Raises:
            UnknownNodeTypeError: if the given node has an unknown type.
        """
        # If the node is a "start" node, just get the next node
        if isinstance(new_node, StartNode):
            new_node_id = new_node.get_next_node_id(self._variables)
            self._add_new_nodes(new_node_id, None)

        # If the node is "stop" node, do nothing
        elif isinstance(new_node, StopNode):
            pass

        # If the node is a "parallel split", get all next nodes
        elif isinstance(new_node, ParallelSplitNode):
            next_node_ids = new_node.get_next_node_id(self._variables)
            self._add_new_nodes(next_node_ids, new_node.nid)

        # If the node is a "parallel sync"...
        elif isinstance(new_node, ParallelSyncNode):
            # Initialize this parallel sync node if not already done
            if not new_node.is_sync_initialized():
                # This synchronization node must wait for all its
                # possible previous nodes.
                new_node.set_nodes_to_sync(
                    self._seqreader.get_prev_node_ids(new_node.nid))

            # Update the history with the previous node
            new_node.add_to_history(new_node.previous_node_id)

            # If all transitions met the parallel_sync
            # Get the next node after the parallel_sync
            if new_node.is_sync_complete():
                new_node.clear_history()
                new_node_id = new_node.get_next_node_id(self._variables)
                self._add_new_nodes(new_node_id, new_node.nid)

        # If the node is of type 'variable', evaluate expressions
        elif isinstance(new_node, VariableNode):
            var_dict = new_node.variables
            # Do not allow to modify read-only sequence variables
            inter = self._read_only_var.intersection(set(var_dict.keys()))
            if inter:
                raise ReadOnlyError(("Node {} tries to modify variables "
                                     "{} but they are read-only variables."
                                     "").format(new_node.nid, inter))
            # Evaluate expression for each variable
            for var_name, expr in var_dict.items():
                if type(expr) is str:
                    value = eval(expr)
                else:
                    # If the expression is not an expression but directly
                    # a value, do not evaluate it.
                    value = expr
                # Update the writeable sequence variable
                self._variables[var_name] = value
        elif isinstance(new_node, FunctionNode):
            # Start the node function in a separated process
            func_callable = self._funcgrab.get_function(new_node.function_name)
            process = mp.Process(
                target=self._run_node_function_with_timeout,
                name="Node {}".format(new_node.nid),
                kwargs={'func': func_callable,
                        'node_id': new_node.nid,
                        'result_queue': self._result_queue,
                        'kwargs': new_node.function_kwargs,
                        'timeout': new_node.timeout})
            process.start()
            # Store this process in the dict of running nodes
            self._running_nodes[new_node.nid] = process
        else:
            raise UnknownNodeTypeError("Type of new node is "
                                       "unknown: {}".format(type(new_node)))

    def _manage_new_result(self, new_result: FunctionNodeResult):
        """Manage a new result in the running sequence.

        Warning:
            This method should only be used in the run() function of this class.
            It modifies the internal state of the SequenceRunner object.

        Args:
            new_result: the FunctionNodeResult object.

        """
        # Save this result into the sequence variables
        self._variables['results'][new_result.nid] = new_result

        # Remove this node from the running nodes
        self._running_nodes.pop(new_result.nid)

        # Get the next node according to transitions
        # and add it to the set of new nodes
        node_object = self._nodes[new_result.nid]
        new_node_id = node_object.get_next_node_id(self._variables)
        self._add_new_nodes(new_node_id, new_result.nid)

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
        """
        # TODO: implement the non blocking feature
        # This implies to manage a new call to "run" after pause has been called

        self.status = SeqRunnerStatus.RUNNING  # useless if blocking call

        # Continue to run the sequence while there are still some nodes to run
        while self._running_nodes or self._new_nodes:

            # Continue to process all the new nodes until none is left
            while self._new_nodes:
                # Retrieve a new node
                new_node = self._new_nodes.pop()
                # Do the appropriate action for this new node
                self._manage_new_node(new_node)

            # Finally, if there are some running nodes,
            # just wait for the end of one of them.
            if self._running_nodes:
                # A single queue is shared by all threads to provide function
                # node results. To know when a function node is over the queue
                # is polled for a result.
                # The queue provides objects of type FunctionNodeResult
                new_result = self._result_queue.get()
                # Process the new result
                self._manage_new_result(new_result)

        self.status = SeqRunnerStatus.STOPPED

    def pause(self):
        # TODO
        raise NotImplemented
        self.status = SeqRunnerStatus.PAUSING
        # Some code...
        self.status = SeqRunnerStatus.PAUSED

    def stop(self):
        # TODO
        raise NotImplemented
        self.status = SeqRunnerStatus.STOPPING
        # Some code
        self.status = SeqRunnerStatus.STOPPED
