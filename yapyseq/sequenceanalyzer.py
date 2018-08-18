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
from .exceptions import SequenceFileError

# Default path to the file used as a schema to check sequences
SEQUENCE_SCHEMA_PATH = "{}/seq_schema.yaml".format(
    os.path.dirname(os.path.realpath(__file__)))


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
        self._seq_id = loaded['sequence']['info']['id']
        self._seq_name = loaded['sequence']['info']['name']
        self._seq_nodes = loaded['sequence']['nodes']
        self._seq_trans = loaded['sequence']['transitions']

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
            Same as `yamale.validate` if it raises others than ValueError
        """
        for f in [seq_file_path, schema_path]:
            if not os.path.isfile(f):
                raise FileNotFoundError("File cannot be found at given "
                                        "path: {}".format(f))

        schema = yamale.make_schema(schema_path)
        data = yamale.make_data(seq_file_path)

        # Validate the sequence
        try:
            yamale.validate(schema, data)
        except ValueError as e:
            raise SequenceFileError(("Errors found in the sequence file: {}"
                                     "\nGot following message:\n"
                                     "{}").format(seq_file_path, str(e)))
        # TODO: check uniqueness of IDs

    def get_sequence_name(self) -> str:
        """Return the name of the sequence.

        Returns:
            Name of the sequence that has been used for initialization.
        """
        pass

    def get_sequence_id(self) -> int:
        """Return the id of the sequence.

        Returns:
            ID of the sequence that has been used for initialization.
        """
        pass

    def get_function_name(self, node_id: int) -> str:
        """Return the function name of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            Name of the function for the given node id.
        """
        pass

    def get_function_arguments(self, node_id: int) -> dict:
        """Return the function arguments of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            A dictionary containing the keyword arguments of the function.
            None if arguments are omitted.
        """
        pass

    def get_node_timeout(self, node_id: int) -> int:
        """Return the node timeout of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            The timeout value, in seconds.
            None if timeout is omitted.
        """
        pass

    def get_node_special(self, node_id: int) -> str:
        """Return the special functionality of a given node.

        Args:
            node_id: the id of the node from which info will be retrieved.

        Returns:
            The name of the special functionality. Name is part of an
            enumeration that can be found in the schema file.
            None if special is omitted.
        """
        pass

    def get_next_node_id(self, src_node_id: int, variables: dict) -> int:
        """Return the next node to run after the given source node.

        Transitions will be analyzed, using the given variables to assess
        their conditions, and winning transition will lead to the next node.

        Args:
            src_node_id: the id of the node which is the source
              of the transitions that will be analyzed.
            variables: dictionary that contains all the variables that the
              conditions of the transitions might require.

        Returns:
            The ID of the next node to run, target of the winning transition.

        Raises:
            MultipleTransitionsError: if no choice can be made between several
              transitions. It means that the conditions of the transitions have
              not anticipated the given set of variables, and allow several
              possibilities. Transitions must be reviewed.
        """
        pass
