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
from enum import Enum

from .functiongrabber import FunctionGrabber
from .sequenceanalyzer import SequenceAnalyzer

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class UnknownTypeError(ValueError):
    pass

# ------------------------------------------------------------------------------
# Custom types for this module
# ------------------------------------------------------------------------------


ExceptInfo = namedtuple("ExceptInfo", "is_raised name args")
NodeResult = namedtuple("NodeResult", "node_id exception returned")
NewNode = namedtuple("NewNode", "node_id previous_node_id")


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

        # Add an empty dict of results in the variables
        # It will be filled with node results while the sequence is running.
        self._variables['results'] = dict()

        # See SequenceRunner.run() for the uses of the following attribute.
        self._result_queue = mp.Queue()

        # Grab all the functions
        # This is where all the imports can fail
        self._funcgrab.import_functions(func_dir,
                                        self._seqanal.get_all_node_functions())

        # Initialize new_nodes
        # A set of node that must be analyzed and run as soon as possible.
        # new_nodes is a set of NewNodes
        # At initialization, previous nodes are set as None
        self._new_nodes: Set[NewNode] = set()
        start_nodes_id = self._seqanal.get_start_node_ids()
        self._add_new_nodes(start_nodes_id, None)

        # Initialize running_nodes
        # A dictionary of nodes that are currently running
        # Node ids are keys, and their processes are values
        self._running_nodes: Dict[int, mp.Process] = dict()

        # Initialize status of synchronization nodes.
        # This variable will be used to manage nodes of type "parallel_sync"
        # It is a dictionary of sets. Each key is the node_id of a
        # "parallel_sync" node, and sets contain the IDs of the transitions
        # that have already been performed to this synchronization node.
        self._parallel_sync_history: Dict[int, Set] = dict()

        # Update status
        self.status = SeqRunnerStatus.INITIALIZED

    @staticmethod
    def _create_node_result(node_id: int, exception: Union[None, Exception],
                            returned_obj: Any) -> NodeResult:
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

        res = NodeResult(node_id, except_info, returned_obj)

        return res

    @staticmethod
    def _run_node_function(func: Callable, node_id: int,
                           result_queue: mp.Queue, kwargs: Dict = None,
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
              function. The stored object will be of type NodeResult.
            kwargs: (optional) The arguments to give to the function.
            timeout: (optional) The time limit for the function to be
              terminated.
        """

        # TODO: manage timeout

        # Run the callable
        try:
            func_res = func(**kwargs)
        except Exception as e:
            res = SequenceRunner._create_node_result(node_id, e, None)
        else:
            res = SequenceRunner._create_node_result(node_id, None, func_res)

        # Provide result through the Queue
        result_queue.put(res)

    def _add_new_nodes(self, new_nodes: Union[int, Set[int]],
                       previous_node: Union[int, None]) -> None:
        """Add one or several new nodes to self._new_nodes.

        Warning:
            This method should only be used in the run() function of this class,
            or during initialization in __init__().
            It modifies the internal state of the SequenceRunner object.

        Args:
            new_nodes: The ID or a set of IDs of the new nodes to add.
            previous_node: the ID of the previous node of the new one.
        """
        if type(new_nodes) is int:
            self._new_nodes.add(NewNode(new_nodes, previous_node))
        elif type(new_nodes) is set:
            self._new_nodes.update([NewNode(n, previous_node)
                                    for n in new_nodes])

    def _manage_special_node(self, new_node: NewNode) -> None:
        """Manage a new node not of type 'function' in the running sequence.

        Warning:
            This method should only be used in the run() function of this class.
            It modifies the internal state of the SequenceRunner object.

        Args:
            new_node: the NewNode object which is not of type 'function'.

        Raises:
            ValueError: if the given new_node is of type 'function'.
            UnknownTypeError: if the given node has an unknown type.
        """
        node_type = self._seqanal.get_node_type(new_node.node_id)
        if node_type == 'function':
            raise ValueError(("This new node (n°{}) is of type 'function'. "
                              "It should not be given to this "
                              "function.").format(new_node.node_id))

        # If the node is a "start" node, just get the next node
        if node_type == "start":
            next_node_id = self._seqanal.get_next_node_id(
                new_node.node_id,
                self._variables)
            self._add_new_nodes(next_node_id, new_node.node_id)

        # If the node is "stop" node, do nothing
        elif node_type == "stop":
            pass

        # If the node is a "parallel split", get all next nodes
        elif node_type == "parallel_split":
            next_node_ids = self._seqanal.get_next_node_id(
                new_node.node_id,
                self._variables)
            self._add_new_nodes(next_node_ids, new_node.node_id)

        # If the node is a "parallel sync"...
        elif node_type == "parallel_sync":
            nnid = new_node.node_id  # just to take less space

            # Initialize the history of this parallel_sync
            # if it does not exist yet
            if nnid not in self._parallel_sync_history:
                self._parallel_sync_history[nnid] = set()

            # Add this node to the history
            self._parallel_sync_history[nnid].add(
                new_node.previous_node_id)

            # If all transitions met the parallel_sync
            # Get the next node after the parallel_sync
            prev = self._seqanal.get_all_prev_node_ids(nnid)
            if prev == self._parallel_sync_history[nnid]:
                self._parallel_sync_history[nnid].clear()
                next_node_id = self._seqanal.get_next_node_id(
                    nnid,
                    self._variables)
                self._add_new_nodes(next_node_id, nnid)
        else:
            raise UnknownTypeError("Type of given node is "
                                   "unknown: {}".format(node_type))


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

        # Continue to run the sequence while there are still some nodes to run
        while self._running_nodes or self._new_nodes:
            # First of all, analyze new nodes and find nodes to start
            nodes_to_start = list()

            # Create a copy of new_nodes for iterations because
            # self._new_nodes will be modified inside the for loop
            new_nodes_iter = self._new_nodes.copy()

            for new_node in new_nodes_iter:
                # Remove this node from the set
                self._new_nodes.remove(new_node)

                # Check if this node is a special node
                node_type = self._seqanal.get_node_type(new_node.node_id)
                if node_type != "function":
                    self._manage_special_node(new_node)
                # If the node is normal, add it to the list of nodes to start
                else:
                    nodes_to_start.append(new_node.node_id)

            # Then, start new processes if their are nodes to run
            for node_id in nodes_to_start:
                # Get all necessary objects to start the new node
                node_func_name = self._seqanal.get_function_name(node_id)
                node_func_call = self._funcgrab.get_function(node_func_name)
                node_func_args = self._seqanal.get_function_arguments(node_id)
                node_timeout = self._seqanal.get_node_timeout(node_id)

                # Start the new node in a process
                process = mp.Process(target=self._run_node_function,
                                     name="Node {}".format(node_id),
                                     kwargs={'func': node_func_call,
                                             'node_id': node_id,
                                             'result_queue': self._result_queue,
                                             'kwargs': node_func_args,
                                             'timeout': node_timeout})
                process.start()
                # Store this process in the dict of running nodes
                self._running_nodes[node_id] = process

            # Finally, if there are some running nodes,
            # just wait for the end of one of them.
            if not self._new_nodes and self._running_nodes:
                # A single queue is shared by all threads to provide function
                # node results. To know when a function node is over the queue
                # is polled for a result.
                # The queue provides objects of type NodeResult
                new_result = self._result_queue.get()

                # Save this result into the sequence variables
                self._variables['results'][new_result.node_id] = new_result

                # Remove this node from the running nodes
                self._running_nodes.pop(new_result.node_id)

                # Get the next node according to transitions
                next_id = self._seqanal.get_next_node_id(new_result.node_id,
                                                         self._variables)

                # Add this next node to new nodes,
                # it will be handled on the next loop iteration
                self._new_nodes.add(NewNode(next_id, new_result.node_id))

        self.status = SeqRunnerStatus.RUNNING  # useless if blocking call

    def pause(self):
        self.status = SeqRunnerStatus.PAUSING
        # Some code...
        self.status = SeqRunnerStatus.PAUSED

    def stop(self):
        self.status = SeqRunnerStatus.STOPPING
        # Some code
        self.status = SeqRunnerStatus.STOPPED
