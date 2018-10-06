#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
import yaml
import yamale
from collections import Counter
from typing import Union, Set, Dict
from abc import ABC

# ------------------------------------------------------------------------------
# MODULE CONSTANTS
# ------------------------------------------------------------------------------

# Default path to the file used as a schema to check sequences
SEQUENCE_SCHEMA_PATH = "{}/seq_schema.yaml".format(
    os.path.dirname(os.path.realpath(__file__)))


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


class IncompatibleNodeType(ValueError):
    pass


# ------------------------------------------------------------------------------
# Sub-objects classes
# ------------------------------------------------------------------------------


class Transition(object)
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
    pass


class ParallelSplitNode(TransitionalNode):
    pass


class ParallelSyncNode(SimpleTransitionalNode):
    pass

# ------------------------------------------------------------------------------
# Main class
# ------------------------------------------------------------------------------


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
      * Arguments of the function for a given node.

    Contents of a sequence file is described in the file `seq_schema.yaml`.

    **The master word of this class is:**
    **Avoid returning complex data structures. Simpler is better.**
    That means that this classes implements a lot of methods to return only
    a single value like an integer or a string, instead of a few methods that
    return a complex dictionary with all the data inside. This choice is made
    to improve the readability of the code which uses this class.
    Therefore, this class is not coded in a very Pythonic way. But this is on
    purpose and a reflected decision. For instance, using properties instead of
    getters would be more Pythonic, but less homogeneous and clear.

    # TODO: implement sub-sequences (detect them. with 'type' maybe ?)
    # TODO: allow transition to use node names instead of ids
    """

    # --------------------------------------------------------------------------
    # Private methods
    # --------------------------------------------------------------------------

    def __init__(self, seq_file_path: str,
                 schema_path: str = SEQUENCE_SCHEMA_PATH):
        """Initialize the SequenceAnalyser with a given sequence.

        Given sequence file is checked using given schema to ensure validity
        of the sequence description. Schema must respect YAMALE syntax.

        Args:
            seq_file_path: Path to a .yaml file describing a sequence.
            schema_path: (optional) Path to a schema YAML file, used by YAMALE.

        Raises:
            Same as `SequenceAnalyzer.check_sequence_file`
        """
        # Check the sequence file. Raises an exception with there is an issue.
        self.check_sequence_file(seq_file_path, schema_path)
        self._seq_file_path = seq_file_path
        self._parse_sequence()

    def _parse_sequence(self):
        """Parse a sequence file to be able to provide information about it.

        Make sure the sequence file is valid before calling this function.
        You can check the file with `SequenceAnalyser.check_sequence`.
        """
        with open(self._seq_file_path) as f:
            loaded = yaml.safe_load(f)

        # Collect data into private attributes
        if ('info' in loaded['sequence'] and
                'name' in loaded['sequence']['info']):
            self._seq_name = loaded['sequence']['info']['name']

        self._seq_nodes = dict((n['id'], n)
                               for n in loaded['sequence']['nodes'])
        self._seq_trans = dict((t['id'], t)
                               for t in loaded['sequence']['transitions'])

    # --------------------------------------------------------------------------
    # Public methods
    # --------------------------------------------------------------------------

    @staticmethod
    def check_sequence_file(seq_file_path: str,
                            schema_path: str = SEQUENCE_SCHEMA_PATH):
        """Check the validity of a given sequence file.

        Given sequence file is checked using given schema to ensure validity
        of the sequence description. Schema must respect YAMALE syntax.

        Args:
            seq_file_path: Path to a YAML file describing a sequence, to check.
            schema_path: (optional) Path to a schema YAML file, used by YAMALE.

        Raises:
            FileNotFoundError: if the given path does not lead to a file.
            IOError: if the file cannot be read.
            SequenceFileError: if format of sequence does not respect the rules.
             See `seq_schema.yaml`.
            Same as `yamale.validate` in case it raises others than ValueError
        """
        for f in [seq_file_path, schema_path]:
            if not os.path.isfile(f):
                raise FileNotFoundError("File cannot be found at given "
                                        "path: {}".format(f))

        schema = yamale.make_schema(schema_path)
        data = yamale.make_data(seq_file_path)

        # Validate most of the sequence structure using the schema
        try:
            yamale.validate(schema, data)
        except ValueError as e:
            raise SequenceFileError(("Errors found in the sequence file: {}"
                                     "\nGot following message:\n"
                                     "{}").format(seq_file_path, str(e)))

        # Check uniqueness of the IDs
        with open(seq_file_path) as f:
            loaded = yaml.safe_load(f)
        for item_type in ['nodes', 'transitions']:
            item_ids = [i['id'] for i in loaded['sequence'][item_type]]
            # Count the occurrence of each ID, and keep those that appear
            # more than once to raise an exception.
            non_unique_ids = [k for k, v in Counter(item_ids).items() if v > 1]
            if non_unique_ids:
                raise SequenceFileError(("The following ids for {} are not "
                                         "unique : {}"
                                         ).format(item_type, *non_unique_ids))

        # TODO: Check that there is no node without transitions.
        # TODO: check compliance between transition IDs and node IDs
        # TODO: check that start nodes do not have IN transitions
        # TODO: check that stop nodes do not have OUT transitions


    def get_all_node_functions(self) -> Set[str]:
        """Get the name of all the node functions in the sequence.

        Only nodes of type 'function' are browsed. Other nodes do not
        provide functions.

        Returns:
            A set of strings being the names of all the node functions in the
            sequence.
        """
        function_names = set()

        # Browse nodes
        for node in self._seq_nodes.values():
            if node['type'] == 'function':
                function_names.add(node['function'])

        return function_names

    def get_start_node_ids(self) -> Set[int]:
        """Get the IDs of all the start nodes in the sequence.

        Returns:
            A Set of integers being the IDs of the nodes of type 'start'.
        """
        start_node_ids = set()

        # Browse nodes
        for node_id, node in self._seq_nodes.items():
            if node["type"] == "start":
                start_node_ids.add(node_id)

        return start_node_ids

    def get_all_prev_node_ids(self, node_id: int) -> Set[int]:
        """Get all the IDs of the nodes that can lead to the given one.

        It will return all the node IDs that have a transition to the given
        node id, regardless the validity of the transitions. It can be seen as
        all the possible ancestors of the given node id.

        Args:
            node_id: the id of the target node.

        Raises:
            KeyError: if the node_id is not a valid node id.
        """
        if node_id not in self._seq_nodes.keys():
            raise KeyError("Node ID {} is not a valid ID.".format(node_id))

        prev_nodes = set([t['source'] for t in self._seq_trans.values()
                          if t['target'] == node_id])

        return prev_nodes


    def get_assignations(self, node_id: int) -> dict:
        """Get assignations of a node of type 'seq_type'.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            A dictionary where keys are variable names and values are
            expressions which have to be evaluated.

        Raises:
            KeyError: if the node_id does not exist in the list of nodes.
            IncompatibleNodeType: if the node is not of type function.
        """
        node_type = self._seq_nodes[node_id]['type']
        if node_type != 'variable':
            raise IncompatibleNodeType(("Cannot retrieve assignations "
                                        "because node {} is of type "
                                        "{}.").format(node_id, node_type))
        return self._seq_nodes[node_id]['assignations']
