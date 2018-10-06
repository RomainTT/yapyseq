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
from typing import Set

from .nodes import StartNode, StopNode, ParallelSplitNode, ParallelSyncNode, \
    FunctionNode, VariableNode

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
