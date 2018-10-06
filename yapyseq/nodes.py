#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Union, Set, Dict


# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class SequenceFileError(ImportError):
    pass


class MultipleTransitionError(RuntimeError):
    pass


class NoTransitionError(RuntimeError):
    pass


class ConditionError(RuntimeError):
    pass


class ParallelSyncFailure(RuntimeError):
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


class TransitionalNode(Node):
    """Class representing a node which contains outgoing transitions.

    This class is not likely to be instantiated, as some children class describe
    the different types of nodes available in a sequence.
    """

    def __init__(self, nid: int, transitions: Set, name: str = None):
        """Initialize a TransitionalNode.

        Args:
            nid: the unique ID of the node.
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
        """
        super().__init__(nid, name)
        self._transitions = set([Transition(t['target'], t['condition'])
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
        """Return the next node to run in function of conditions.

        Transitions will be analyzed, using the given variables to assess
        their conditions, and winning transition(s) will lead to the next
        nodes(s).

        TODO: implement priorities among transitions

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

    This king of node can have several transitions, but when they are evaluated
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
                 function_kwargs: Dict, transitions: Set,
                 name: str = None, timeout: int = None):
        """Initialize a FunctionNode.

        Args:
            nid: the unique ID of the node.
            function_name: the name of the function to run in the node.
            function_kwargs: the keyword arguments to give to the function.
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
            timeout: (optional) the timeout limit of the function, in seconds.
        """
        super().__init__(nid, transitions, name)
        self._function_name = function_name
        self._function_kwargs = function_kwargs
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
        return self._variables
