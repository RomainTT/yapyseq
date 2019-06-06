#!/usr/bin/env python
# coding: utf-8
"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
from collections import Counter, OrderedDict
from typing import Set, Dict
import copy

from ruamel.yaml import YAML
import yamale

from yapyseq.nodes import StartNode, StopNode, ParallelSplitNode, \
    ParallelSyncNode, \
    FunctionNode, VariableNode, TransitionalNode

# ------------------------------------------------------------------------------
# MODULE CONSTANTS
# ------------------------------------------------------------------------------

# Default path to the file used as a schema to check sequences
SEQUENCE_SCHEMA_PATH = "{}/seq_schema.yaml".format(
    os.path.dirname(os.path.realpath(__file__)))

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class SequenceFileError(OSError):
    pass


# ------------------------------------------------------------------------------
# Main class
# ------------------------------------------------------------------------------


class SequenceReader(object):
    """Class that checks, reads, and extract Nodes from a sequence description.

    The aim of an instance of `SequenceReader` is to read a `.yaml` file that
    describes a sequence, create Node objects using parameters from this file,
    and make them available.

    Contents of a sequence file is described in the file `seq_schema.yaml`.

    # TODO: implement sub-sequences
    # TODO: allow transitions to use node names instead of ids OR remove names and ids can be strings
    """

    # --------------------------------------------------------------------------
    # Private methods
    # --------------------------------------------------------------------------

    def __init__(self,
                 seq_file_path: str,
                 schema_path: str = SEQUENCE_SCHEMA_PATH):
        """Initialize the SequenceReader with a given sequence.

        Given sequence file is checked using given schema to ensure validity
        of the sequence description. Schema must respect YAMALE syntax.

        Args:
            seq_file_path: Path to a .yaml file describing a sequence.
            schema_path: (optional) Path to a schema YAML file, used by YAMALE.

        Raises:
            Same as `SequenceReader.check_sequence_file`
        """
        # Save the path to the sequence file
        self._seq_file_path = seq_file_path
        # Initialize the set of nodes
        self._nodes = set()

        # Check the sequence file. Raises an exception if there is an issue.
        self.check_sequence_file(seq_file_path, schema_path)

        # Parse the sequence to create node objects
        self._parse_sequence()

    def _parse_sequence(self):
        """Parse a sequence file to be able to provide information about it.

        Make sure the sequence file is valid before calling this function.
        File can be checked with `SequenceReader.check_sequence`.
        """
        with open(self._seq_file_path) as f:
            yaml = YAML(typ='safe')
            yaml.preserve_quotes = True
            loaded = yaml.load(f)

        # Collect constants
        if 'constants' in loaded['sequence']:
            self._constants = loaded['sequence']['constants']
        else:
            self._constants = dict()

        # Create node objects
        for node_dict in loaded['sequence']['nodes']:
            ntype = node_dict['type']

            if ntype == "function":
                # list of wrappers is converted into an OrderedDict
                wrapper_list = node_dict.get('wrappers')
                if wrapper_list:
                    wrapper_dict = OrderedDict()
                    for wrapper in wrapper_list:
                        # A wrapper can be written as a simple string (name)
                        # or as a dict if some arguments are given.
                        if isinstance(wrapper, str):
                            wrapper_dict[wrapper] = {}
                        elif isinstance(wrapper, dict):
                            wrapper_dict.update(wrapper)
                        else:
                            raise SequenceFileError(
                                ('The following wrapper is neiter a str '
                                 ' or a dict: {}').format(wrapper))
                else:
                    wrapper_dict = None
                # create function node
                new_node = FunctionNode(
                    nid=node_dict.get('id'),
                    name=node_dict.get('name'),
                    transitions=node_dict.get('transitions'),
                    function_name=node_dict.get('function'),
                    function_kwargs=node_dict.get('arguments'),
                    timeout=node_dict.get('timeout'),
                    return_var_name=node_dict.get('return'),
                    wrappers=wrapper_dict)

            elif ntype == "start":
                new_node = StartNode(nid=node_dict.get('id'),
                                     name=node_dict.get('name'),
                                     transitions=node_dict.get('transitions'))

            elif ntype == "stop":
                new_node = StopNode(nid=node_dict.get('id'),
                                    name=node_dict.get('name'))

            elif ntype == "variable":
                new_node = VariableNode(
                    nid=node_dict.get('id'),
                    name=node_dict.get('name'),
                    transitions=node_dict.get('transitions'),
                    variables=node_dict.get('variables'))

            elif ntype == "parallel_split":
                new_node = ParallelSplitNode(
                    nid=node_dict.get('id'),
                    name=node_dict.get('name'),
                    transitions=node_dict.get('transitions'))

            elif ntype == "parallel_sync":
                new_node = ParallelSyncNode(
                    nid=node_dict.get('id'),
                    name=node_dict.get('name'),
                    transitions=node_dict.get('transitions'))

            else:
                raise SequenceFileError("Node n°{} has an unknown type "
                                        "{}.".format(node_dict['id'],
                                                     node_dict['type']))
            # Add the new node to set of nodes in the SequenceReader
            self._nodes.add(new_node)

        # TODO: Set required history for parallel sync node HERE

    # --------------------------------------------------------------------------
    # Public methods
    # --------------------------------------------------------------------------

    @staticmethod
    def check_sequence_file(seq_file_path: str,
                            schema_path: str = SEQUENCE_SCHEMA_PATH):
        """Check the validity of a given sequence file.

        Given sequence file is checked using given schema to ensure validity
        of the sequence description. Schema must respect YAMALE syntax.
        # TODO: add description of additional checks
        # TODO: add check of constant names (must be string)

        Args:
            seq_file_path: Path to a YAML file describing a sequence, to check.
            schema_path: (optional) Path to a schema YAML file, used by YAMALE.

        Raises:
            FileNotFoundError: if the given path does not lead to a file.
            OSError: if the file cannot be read.
            SequenceFileError: if format of sequence does not respect the rules.
             See `seq_schema.yaml`.
            Same as `yamale.validate` in case it raises others than ValueError
        """
        if not os.path.isfile(seq_file_path):
            raise FileNotFoundError("Sequence file cannot be found at given "
                                    "path: {}".format(seq_file_path))

        if not os.path.isfile(schema_path):
            raise FileNotFoundError("Schema file cannot be found at given "
                                    "path: {}".format(schema_path))

        schema = yamale.make_schema(schema_path)
        data = yamale.make_data(seq_file_path)

        # Validate most of the sequence structure using the schema
        try:
            yamale.validate(schema, data)
        except ValueError as e:
            raise SequenceFileError(("Errors found in the sequence file: {}"
                                     "\nGot following message:\n"
                                     "{}").format(seq_file_path, str(e)))

        # Load the sequence file
        with open(seq_file_path) as f:
            yaml = YAML(typ='safe')
            yaml.preserve_quotes = True
            loaded = yaml.load(f)

        # Check uniqueness of the IDs
        item_ids = [i['id'] for i in loaded['sequence']['nodes']]
        # Count the occurrence of each ID, and keep those that appear
        # more than once to raise an exception.
        non_unique_ids = [k for k, v in Counter(item_ids).items() if v > 1]
        if non_unique_ids:
            raise SequenceFileError(
                "The following ids for nodes are not unique :"
                " {}".format(*non_unique_ids))

        # Check compliance between transition IDs and node IDs
        # And check that start nodes do not have IN transitions
        # First, get all the ids of start nodes
        start_nids = [
            i['id'] for i in loaded['sequence']['nodes'] if i['type'] == "start"
        ]
        # Then, browse every node to check its transitions
        for node in loaded['sequence']['nodes']:
            if 'transitions' in node:
                transitions = node['transitions']
                targets = set([t['target'] for t in transitions])
            else:
                targets = set()
            # Check that the IDs exist
            wrong_nids = targets.difference(set(item_ids))
            if wrong_nids:
                raise SequenceFileError(("Node with ID n°{} has transitions"
                                         " with nonexistent targets:"
                                         " {}".format(node['id'], wrong_nids)))
            # Check that the target is not a start node
            wrong_nids = targets.intersection(set(start_nids))
            if wrong_nids:
                raise SequenceFileError(("Node with ID n°{} has transitions"
                                         " leading to start nodes {}"
                                         "").format(node['id'], wrong_nids))

    def get_nodes(self) -> Set:
        """Get the instantiated Node objects creating during parsing.

        Returns:
            A Set of Node objects (can be different classes in function of the
            node type), created during parsing of the sequence file.
            A copy of the original is sent, in order to avoid modifications of
            the original content.
        """
        return copy.deepcopy(self._nodes)

    def get_node_dict(self) -> Dict:
        """Get a dict of the instantiated Node objects creating during parsing.

        Returns:
            A dictionary where keys are the IDs of the nodes, and values
            are the Node objects (can be different classes in function of the
            node type), created during parsing of the sequence file.
            A copy of the original is sent, in order to avoid modifications of
            the original content.
        """
        node_dict = dict([(n.nid, n) for n in self._nodes])
        return copy.deepcopy(node_dict)

    def get_constants(self) -> Dict:
        """Get the constants defined in the sequence file.

        Returns:
            A dictionary where keys are the names of the constants, and values
            are their values.
            A copy of the original is sent, in order to avoid modifications of
            the original content.
        """
        return copy.deepcopy(self._constants)

    def get_node_function_names(self) -> Set[str]:
        """Get the name of all the node functions in the sequence.

        Returns:
            A set of strings being the names of all the node functions in the
            sequence.
        """
        return set(
            [n.function_name for n in self._nodes if type(n) is FunctionNode])

    def get_node_wrapper_names(self) -> Set[str]:
        """Get the name of all the node wrappers in the sequence.

        Returns:
            A set of strings being the names of all the node wrappers in the
            sequence.
        """
        all_names = set()
        for node in self._nodes:
            if type(node) is FunctionNode:
                all_names.update(node.wrapper_names)
        return all_names

    def get_start_node_ids(self):
        """Get the IDs of all the start nodes in the sequence.

        Returns:
            A Set of integers being the IDs of the nodes of type 'start'.
        """
        return set([n.nid for n in self._nodes if type(n) is StartNode])

    def get_prev_node_ids(self, node_id: int) -> Set[int]:
        """Get the IDs of all the nodes that can lead to the given one.

        It will return the IDs of all the nodes that have a transition to the
        given node id, regardless the validity of the transitions. It can be
        seen as all the possible ancestors of the given node id.

        Args:
            node_id: the id of the target node.

        Returns:
            A set of node ids.

        Raises:
            KeyError: if the node_id is not a valid node id.
        """
        # Initialize the value that will be returned
        previous_node_ids = set()

        # Browser nodes
        for node in self._nodes:
            # Only browse transitional nodes
            if issubclass(type(node), TransitionalNode):
                next_nodes = node.get_all_next_node_ids()
                # If given nid is in the target list, add this previous node
                if node_id in next_nodes:
                    previous_node_ids.add(node.nid)

        return previous_node_ids
