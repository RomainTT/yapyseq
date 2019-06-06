#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Dict, Set, Union, Any
import multiprocessing as mp
from enum import Enum
from logging import Logger
import os

from yapyseq.functiongrabber import FunctionGrabber
from yapyseq.sequencereader import SequenceReader
from yapyseq.nodes import FunctionNode, StartNode, StopNode, VariableNode, \
    ParallelSyncNode, ParallelSplitNode, FunctionNodeResult
from yapyseq.logger import get_logger
from yapyseq.common import evaluate_expr

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class UnknownNodeTypeError(ValueError):
    pass


class ReadOnlyError(ValueError):
    pass


# ------------------------------------------------------------------------------
# Custom types for this module
# ------------------------------------------------------------------------------


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

    def __init__(self, sequence_path: str, func_dir: str,
                 constants: dict = None,
                 logger: Union[bool, Logger] = True):
        """Initialize the runner with a given sequence.

        Args:
            func_dir: directory where to search the node functions for.
            sequence_path: path to the sequence file to run.
            constants: sequence constants given for this run.
            logger: this configures the logger and can have the following
                values:
                    * False to disable the logger.
                    * True to enable the default logger in console.
                    * A logging.Logger object to use this one to log. It must be
                      already configured.

        Raises:
            Exceptions from SequenceAnalyzer and FunctionGrabber.
        """
        # Create logger
        # Get the name of the sequence file without the extension
        self.basename = os.path.splitext((os.path.basename(sequence_path)))[0]
        entry_format = ('%(asctime)s - %(name)s - %(levelname)s '
                        '- seq. {} - %(message)s').format(self.basename)
        if logger is False:
            self._logger = get_logger(name=__name__,
                                      entry_format=entry_format,
                                      disabled=True)
        elif logger is True:
            self._logger = get_logger(name=__name__,
                                      entry_format=entry_format)
        elif isinstance(logger, Logger):
            self._logger = logger
        else:
            raise ValueError("logger must be either a boolean or a "
                             "logging.Logger instance.")

        self._logger.info('Started initialization of sequence '
                          '{} now referred as {}'.format(sequence_path,
                                                         self.basename))

        # Create basic objects
        self._funcgrab = FunctionGrabber()
        self._seqreader = SequenceReader(sequence_path)

        # Define the set of variables that are read-only
        # There are yapyseq built-in variables, sequence constants,
        # and given constants
        self._read_only_var = {'results'}
        self._read_only_var.update(self._seqreader.get_constants())
        if constants:
            self._read_only_var.update(constants.keys())

        # Initialize the dictionary of variables.
        # It contains both read-only and writeable variables
        self._variables = dict()
        if constants:
            self._variables.update(constants)
        self._variables.update(self._seqreader.get_constants())
        # Add an empty dict of results in the variables
        # It will be filled with node results while the sequence is running.
        self._variables['results'] = dict()

        # See SequenceRunner.run() for the uses of the following attribute.
        self._result_queue = mp.Queue()

        # Grab all functions and wrappers
        # This is where all the imports can fail
        self._funcgrab.import_functions(
            func_dir,
            self._seqreader.get_node_function_names())
        self._funcgrab.import_wrappers(
            func_dir,
            self._seqreader.get_node_wrapper_names())

        # Get the dictionary of nodes
        # keys are the nids, and values the node objects
        self._nodes = self._seqreader.get_node_dict()

        # Set callable of each nodes with the ones imported earlier
        # This is necessary before running the nodes
        for node in self._nodes.values():
            if isinstance(node, FunctionNode):
                node.function_callable = self._funcgrab.get_function(
                    node.function_name)
                node.wrapper_classes = self._funcgrab.get_wrappers(
                    node.wrapper_names)

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

        self._logger.info(('Finished initialization of sequence {}'
                           ).format(self.basename))


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
        # ----------------------------------------------------------------------
        # If the node is a "start" node, just get the next node
        if isinstance(new_node, StartNode):
            next_node_ids = new_node.get_next_node_id(self._variables)
            self._add_new_nodes(next_node_ids, None)
            self._logger.info(('Node {} engaged. Type is "start". '
                               'Next node is {}').format(new_node.nid,
                                                         next_node_ids.pop()))

        # ----------------------------------------------------------------------
        # If the node is "stop" node, do nothing
        elif isinstance(new_node, StopNode):
            self._logger.info(('Node {} engaged. Type is "stop". '
                               'Nothing to do.').format(new_node.nid))
            pass

        # ----------------------------------------------------------------------
        # If the node is a "parallel split", get all next nodes
        elif isinstance(new_node, ParallelSplitNode):
            next_node_ids = new_node.get_next_node_id(self._variables)
            self._add_new_nodes(next_node_ids, new_node.nid)
            self._logger.info(('Node {} engaged. Type is "parallel split". '
                               'Next nodes are {}').format(new_node.nid,
                                                           next_node_ids))

        # ----------------------------------------------------------------------
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
                next_node_ids = new_node.get_next_node_id(self._variables)
                self._add_new_nodes(next_node_ids, new_node.nid)
                self._logger.info(('Node {} engaged. Type is "parallel sync". '
                                   'Synchronisation is completed. '
                                   'Next node is {}').format(
                                        new_node.nid,
                                        next_node_ids.pop()))
            else:
                self._logger.info(('Node {} engaged. Type is "parallel sync". '
                                   'Synchronisation is not completed yet.'
                                   ).format(new_node.nid))

        # ----------------------------------------------------------------------
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
                value = evaluate_expr(expr, self._variables)
                # Update the writeable sequence variable
                self._variables[var_name] = value
            # Apply transition
            next_node_ids = new_node.get_next_node_id(self._variables)
            self._add_new_nodes(next_node_ids, None)
            self._logger.info(('Node {} engaged. Type is "variable". '
                               'Next node is {}').format(new_node.nid,
                                                         next_node_ids.pop()))

        # ----------------------------------------------------------------------
        # if the node is of type "function", run the function in a process
        elif isinstance(new_node, FunctionNode):
            # Create a new Process to run this function
            process = mp.Process(
                target=new_node.run,
                name="Node {}".format(new_node.nid),
                kwargs={'result_queue': self._result_queue,
                        'variables': self._variables.copy()})
            process.start()
            # Store this process in the dict of running nodes
            self._running_nodes[new_node.nid] = process
            self._logger.info(('Node {} engaged. Type is "function". '
                               'Function is started.').format(new_node.nid))

        # ----------------------------------------------------------------------
        else:
            raise UnknownNodeTypeError(("Type of node {} is unknown: {}"
                                        ).format(new_node.nid, type(new_node)))

    def _manage_new_function_result(self,
                                    new_result: FunctionNodeResult):
        """Manage a new result of FunctionNode in the running sequence.

        Warning:
            This method should only be used in the run() function of this class.
            It modifies the internal state of the SequenceRunner object.

        Args:
            new_result: the FunctionNodeResult object.

        """
        # Get the node of the result
        node_object = self._nodes[new_result.nid]

        # Save this result into the sequence variables
        self._variables['results'][new_result.nid] = new_result

        # If a name has been given, store the return object into a
        # sequence variable with this name.
        if node_object.return_var_name:
            self._variables[node_object.return_var_name] = new_result.returned

        # Remove this node from the running nodes
        self._running_nodes.pop(new_result.nid)

        # Get the next node according to transitions
        # and add it to the set of new nodes
        next_node_ids = node_object.get_next_node_id(self._variables)
        self._add_new_nodes(next_node_ids, new_result.nid)

        self._logger.info(('Function node {} is terminated. Next node is '
                           '{}.').format(new_result.nid, next_node_ids.pop()))

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

        self._logger.info('Running sequence {}'.format(self.basename))
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
                self._logger.debug(('There are currently {} running '
                                    'nodes.').format(len(self._running_nodes)))
                # A single queue is shared by all threads to provide function
                # node results. To know when a function node is over the queue
                # is polled for a result.
                # The queue provides objects of type FunctionNodeResult
                new_result = self._result_queue.get()
                # Process the new result
                self._manage_new_function_result(new_result)

        self.status = SeqRunnerStatus.STOPPED
        self._logger.info('END of the run of sequence {}'.format(self.basename))

    def pause(self):
        # TODO
        raise NotImplemented
        self._logger.info('Pausing sequence {}'.format(self.basename))
        self.status = SeqRunnerStatus.PAUSING
        # Some code...
        self.status = SeqRunnerStatus.PAUSED

    def stop(self):
        # TODO
        raise NotImplemented
        self._logger.info('Stopping sequence {}'.format(self.basename))
        self.status = SeqRunnerStatus.STOPPING
        # Some code
        self.status = SeqRunnerStatus.STOPPED

    @property
    def variables(self) -> Dict:
        """Copy of the current sequence variables (read-only)."""
        return dict(self._variables)
