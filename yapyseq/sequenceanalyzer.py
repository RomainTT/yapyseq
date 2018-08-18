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
      * Give parameters of the function for a given node.

    Contents of a sequence file is described in the file `seq_schema.yaml`.
    """

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
