#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Callable, Union, Set, Dict, Any
from collections import namedtuple
import multiprocessing as mp
from queue import Empty as EmptyQueueException

# ------------------------------------------------------------------------------
# Custom types for this module
# ------------------------------------------------------------------------------

ExceptInfo = namedtuple("ExceptInfo", "is_raised name object")
FunctionNodeResult = namedtuple("FunctionNodeResult",
                                "nid exception returned")

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class MultipleTransitionError(RuntimeError):
    pass


class NoTransitionError(RuntimeError):
    pass


class ConditionError(RuntimeError):
    pass


class ParallelSyncFailure(RuntimeError):
    pass


class PreviousNodeUndefined(ReferenceError):
    pass


class NodeFunctionTimeout(TimeoutError):
    pass

# ------------------------------------------------------------------------------
# Main classes
# ------------------------------------------------------------------------------


class Transition(object):
    """Class representing a transition."""

    def __init__(self, target: int, condition: str = None):
        """Initialize a Transition.

        Args:
            target: the nid of the targeted Node.
            condition: (optional) the condition to fulfill for this transition.
        """
        self._target = target
        self._condition = condition

    @property
    def target(self):
        return self._target

    def is_condition_fulfilled(self, variables: Dict):
        """Check if the condition is fulfilled with the given variables.

        Args:
            variables: a dictionary of variables that will be used to evaluate
              the condition.
        """
        # If there is no condition, it is considered as fulfilled
        if self._condition is None:
            return True

        # Evaluate the condition as a Python expression.
        # None is given as globals and variables are given as locals
        cond_res = eval(self._condition, None, variables)

        # If condition does not return a bool, raise an error
        if type(cond_res) is not bool:
            raise ConditionError("The following condition did not "
                                 "return a boolean : "
                                 "{}".format(self._condition))
        # Else, return the result
        else:
            return cond_res


class Node(object):
    """Class representing a Node.

    This class is not likely to be instantiated, as some children class describe
    the different types of nodes available in a sequence.
    """

    def __init__(self, nid: int, name: str = None):
        """Initialize a Node.

        Args:
            nid: the unique ID of the node.
            name: (optional) the name of the node.
        """
        self._nid = nid
        self._name = name
        self._previous_node_id = None

    @property
    def nid(self) -> int:
        """The unique ID of the node (read-only)."""
        return self._nid

    @property
    def name(self) -> str:
        """The name of the node. (read-only)

        Name is None if no name has been provided.
        """
        return self._name

    @property
    def previous_node_id(self):
        """The saved previous node id of this node.

        Raises:
            PreviousNodeUndefined: if no previous node is saved.
        """
        if self._previous_node_id:
            return self._previous_node_id
        else:
            raise PreviousNodeUndefined("Trying to get the previous node id"
                                        "but it is unknown...")

    @previous_node_id.setter
    def previous_node_id(self, value):
        self._previous_node_id = value


class TransitionalNode(Node):
    """Class representing a node which contains outgoing transitions.

    This class is not likely to be instantiated, as some children class describe
    the different types of nodes available in a sequence.
    """

    def __init__(self, nid: int, transitions: Set, name: str = None):
        """Initialize a TransitionalNode.

        Args:
            nid: the unique ID of the node.
            transitions: the outgoing transitions of the node. Each item of the
              set must be a dictionary with the keys 'target' and 'condition',
              where 'target' contains the ID of the targeted node, and
              'condition', the Python expression to assess.
              'condition' is optional.
            name: (optional) the name of the node.
        """
        super().__init__(nid, name)
        self._transitions = set([Transition(t.get('target'), t.get('condition'))
                                 for t in transitions])

    def get_all_next_node_ids(self) -> Set[int]:
        """Get the IDs of every nodes that can be reached from this one.

        It will return all the node IDs that are targeted by this current node,
        regardless the validity of the transitions. It can be seen as all the
        possible next nodes.

        Returns:
            A set of integers being the node ids of the possible next nodes.
        """
        return set([t.target for t in self._transitions])

    def get_next_node_id(self, variables: dict) -> Union[int, Set[int]]:
        """Return the ids of the next node to run in function of conditions.

        Transitions will be analyzed, using the given variables to assess
        their conditions, and winning transition(s) will lead to the next
        nodes(s).

        TODO: implement priorities among transitions
        TODO: implement the 'else' in conditions

        Args:
            variables: dictionary that contains all the variables that the
              conditions of the transitions might require. This dictionary will
              be added to the local variables before evaluating the condition
              expression.

        Returns:
            A set containing the IDs of all the next nodes to run next.

        Raises:
            NoTransitionError: if no transition is possible.
        """
        # This set will contain the conditions with a fulfilled condition
        winning_transitions = set()

        # For each candidate, check the condition
        for transition in self._transitions:
            if transition.is_condition_fulfilled(variables):
                winning_transitions.add(transition)

        # Create the set of target nodes, based on the winning transitions
        target_nodes = set(t.target for t in winning_transitions)

        # Check to raise NoTransitionError
        # A node MUST have at least one output transition.
        if len(target_nodes) == 0:
            raise NoTransitionError(("Node n°{} does not have any successful "
                                     "transition.").format(self.nid))

        return target_nodes


class SimpleTransitionalNode(TransitionalNode):
    """Class representing a node that can have only one transition target.

    This kind of node can have several transitions, but when they are evaluated
    to find the next node, only one transition can win.
    """

    def get_next_node_id(self, variables: dict):
        """Overriding of parent class.

        Raises:
            MultipleTransitionError: if several transitions are fulfilled at
              the same time, and therefore give several next nodes.
        """
        next_nodes = super().get_next_node_id(variables)
        if len(next_nodes) > 1:
            raise MultipleTransitionError(
                "Start node n°{} has several transition targets ({}) "
                "but it is forbidden.".format(self.nid, next_nodes))
        else:
            return next_nodes


class StartNode(SimpleTransitionalNode):
    """Class representing a node of type start."""
    pass


class StopNode(Node):
    """Class representing a node of type stop."""
    pass


class ParallelSplitNode(TransitionalNode):
    """Class representing a node of type 'parallel split'."""
    pass


class ParallelSyncNode(SimpleTransitionalNode):
    """Class representing a node of type 'parallel sync'."""

    def __init__(self, nid: int, transitions: Set, name: str = None):
        """Initialize a ParallelSyncNode.

        Args:
            nid: the unique ID of the node.
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
        """
        super().__init__(nid, transitions, name)
        # sync_history is the history of synchronization for a ParallelSyncNode.
        # It keeps track of the IDs of the previous nodes that led to this
        # synchronization node.
        self._sync_history = set()

        # the set of nodes that this ParallelSyncNode must synchronize.
        # It must set after initialization.
        self._nodes_to_sync = set()

    def set_nodes_to_sync(self, nids: Set[int]):
        """Set the list of nid to synchronize through this ParallelSyncNode.

        Args:
            nids: set containing the NIDs of the nodes that are targeting this
              ParallelSyncNode.
        """
        self._nodes_to_sync = nids

    def is_sync_initialized(self):
        """Check if the nodes to sync have been already declared."""
        return len(self._nodes_to_sync) > 0

    def is_sync_complete(self):
        """Check if the synchronization process of this node is complete."""
        if len(self._nodes_to_sync) == 0:
            raise ParallelSyncFailure(
                "Cannot check synchronization for node n°{}. "
                "Set of nodes to synchronize has not been "
                "initialized.".format(self.nid))
        if self._nodes_to_sync == self._sync_history:
            return True
        else:
            return False

    def clear_history(self):
        self._sync_history = set()

    def add_to_history(self, nid):
        self._sync_history.add(nid)


class FunctionNode(SimpleTransitionalNode):
    """Class representing a node of type function."""

    def __init__(self, nid: int, function_name: str,
                 transitions: Set, function_kwargs: Dict = None,
                 name: str = None, timeout: int = None):
        """Initialize a FunctionNode.

        Args:
            nid: the unique ID of the node.
            function_name: the name of the function to run in the node.
            function_kwargs: (optional) the keyword arguments to give
              to the function.
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
            timeout: (optional) the timeout limit of the function, in seconds.
        """
        super().__init__(nid, transitions, name)
        self._function_name = function_name
        self._function_kwargs = function_kwargs if function_kwargs else dict()
        self._timeout = timeout

    @property
    def function_name(self) -> str:
        """The name of the function to run in the node (read-only)."""
        return self._function_name

    @property
    def function_kwargs(self) -> Dict:
        """The keyword arguments of the function to run (read-only)."""
        return self._function_kwargs

    @property
    def timeout(self):
        """The timeout limit of the function, in seconds (read-only).

        Timeout is None if no timeout has been provided."""
        return self._timeout

    @staticmethod
    def _create_node_result(node_id: int, exception: Union[None, Exception],
                            returned_obj: Any) -> FunctionNodeResult:
        """Return an easy data structure containing result of a node.

        Args:
            exception: the exception object if the function raised one.
            returned_obj: the returned object if the function returned one.

        Returns:
            A namedtuple containing all the given data in a structured form.
        """
        if exception:
            except_info = ExceptInfo(True,
                                     type(exception).__name__,
                                     exception)
        else:
            except_info = ExceptInfo(False, None, None)

        res = FunctionNodeResult(node_id,
                                 except_info,
                                 returned_obj)
        return res

    @staticmethod
    def _run_function_no_timeout(func: Callable, node_id: int,
                                 result_queue: mp.Queue,
                                 kwargs: Dict = None) -> None:
        """Function that can be called in a thread to run a node function.

        This function does:
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
            res = FunctionNode._create_node_result(node_id, e, None)
        else:
            res = FunctionNode._create_node_result(node_id, None, func_res)

        # Provide result through the Queue
        result_queue.put(res)

    @staticmethod
    def _run_function_with_timeout(func: Callable, node_id: int,
                                   result_queue: mp.Queue,
                                   kwargs: Dict = None,
                                   timeout: int = None) -> None:
        """Function that can be called in a thread to run a node function.

        This function does:
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
            FunctionNode._run_function_no_timeout(
                func, node_id, result_queue, kwargs)
        else:
            # Create a sub-result queue for the real run of the function
            sub_result_queue = mp.Queue()
            # Start the function in the new sub-thread
            process = mp.Process(
                target=FunctionNode._run_function_no_timeout,
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
                result = FunctionNode._create_node_result(
                    node_id, exception, None)
            finally:
                # Put the final result in the result queue
                result_queue.put(result)


class VariableNode(SimpleTransitionalNode):
    """Class representing a node of type variable."""

    def __init__(self, nid: int, variables: Dict,
                 transitions: Set, name: str = None):
        """Initialize a VariableNode.

        Args:
            nid: the unique ID of the node.
            variables: a dictionary of variables and their assignations in
              the form of {var_name: python_expression}
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
        """
        super().__init__(nid, transitions, name)
        self._variables = variables

    @property
    def variables(self):
        """Dictionary of variables with python expressions as values."""
        return self._variables

# TODO: SequenceNode
