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
from typing import Union, List, Set

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

    # TODO: implement sub-sequences (detect them. with 'special' maybe ?)
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

    def get_sequence_name(self) -> str:
        """Return the name of the sequence.

        Returns:
            Name of the sequence that has been used for initialization.
        """
        return self._seq_name

    def get_function_name(self, node_id: int) -> str:
        """Return the function name of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            Name of the function for the given node id.

        Raises:
            KeyError: if the node_id does not exist in the list of nodes.
        """
        return self._seq_nodes[node_id]['function']

    def get_function_arguments(self, node_id: int) -> Union[dict, None]:
        """Return the function arguments of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            A dictionary containing the keyword arguments of the function.
            None if arguments are omitted.

        Raises:
            KeyError: if the node_id does not exist in the list of nodes.
        """
        node = self._seq_nodes[node_id]
        try:
            return node['arguments']
        except KeyError:
            return None

    def get_node_timeout(self, node_id: int) -> Union[int, None]:
        """Return the node timeout of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            The timeout value, in seconds.
            None if timeout is omitted.

        Raises:
            KeyError: if the node_id does not exist in the list of nodes.
        """
        node = self._seq_nodes[node_id]
        try:
            return node['timeout']
        except KeyError:
            return None

    def get_node_special(self, node_id: int) -> Union[str, None]:
        """Return the special functionality of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            The name of the special functionality. Name is part of an
            enumeration that can be found in the schema file.
            None if special is omitted.

        Raises:
            KeyError: if the node_id does not exist in the list of nodes.
        """
        node = self._seq_nodes[node_id]
        try:
            return node['special']
        except KeyError:
            return None

    def get_next_node_id(self, src_node_id: int, variables: dict) -> List[int]:
        """Return the next node to run after the given source node.

        Transitions will be analyzed, using the given variables to assess
        their conditions, and winning transition will lead to the next nodes(s).

        Args:
            src_node_id: the id of the node which is the source
              of the transitions that will be analyzed.
            variables: dictionary that contains all the variables that the
              conditions of the transitions might require.

        Returns:
              A list of IDs of every next nodes to run,
              targets of the winning transitions.

        Raises:
            KeyError: if the src_node_id is not a valid node id.
        """
        if src_node_id not in self._seq_nodes.keys():
            raise KeyError("Node ID {} is not a valid ID.".format(src_node_id))

        # Get all the transitions that have src_node_id as source
        candidate_ids = [t_id for t_id, t in self._seq_trans.items()
                         if t['source'] == src_node_id]

        # Allowed transitions are named 'winners'
        winner_ids = list()

        # For each candidate, check the condition
        for cid in candidate_ids:
            # If transition has no condition, it is immediately a winner
            if 'condition' not in self._seq_trans[cid]:
                winner_ids.append(cid)
            # Else, evaluate the condition of the transition
            else:
                cond = self._seq_trans[cid]['condition']
                # Evaluate the condition.
                # None is given as globals,
                # and variables are given as locals
                cond_res = eval(cond, None, variables)
                # If condition does not return a bool, raise an error
                if type(cond_res) is not bool:
                    raise ConditionError("The following condition does not "
                                         "return a boolean : "
                                         "{}".format(cond))
                # If condition is True, then append this transition to winners
                if cond_res is True:
                    winner_ids.append(cid)

        # Create the list of target nodes, based on the transition winners
        target_nodes = list(set(
            [t['target'] for t in self._seq_trans.values()
             if t['id'] in winner_ids]))

        return target_nodes

    def get_all_node_functions(self) -> Set[str]:
        """Get the name of all the node functions in the sequence.

        Only nodes without a non-null parameter "special" are considered.
        Nodes that have a "special" functionality do not need to provide a
        function.

        Returns:
            A set of strings being the names of all the node functions in the
            sequence. Except for "special" nodes.
        """
        function_names = set()

        # Browse nodes
        for node in self._seq_nodes.values():
            # Avoid special nodes
            if "special" not in node:
                function_names.add(node['function'])

        return function_names

    def get_start_node_ids(self) -> Set[int]:
        """Get the IDs of all the start nodes in the sequence.

        Returns:
            A Set of integers being the IDs of the nodes with a key "special"
            of value "start".
        """
        start_node_ids = set()

        # Browse nodes
        for node_id, node in self._seq_nodes.items():
            # Check only special nodes
            if "special" in node and node["special"] == "start":
                start_node_ids.add(node_id)

        return start_node_ids
