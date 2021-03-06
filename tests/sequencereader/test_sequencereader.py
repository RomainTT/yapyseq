#!/usr/bin/env python
# coding: utf-8

import pytest
import os

from yapyseq.sequencereader import *
from yapyseq.nodes import *

VALID_SEQ_PATH = "tests/sequencereader/sequences/valid"
INVALID_SEQ_PATH = "tests/sequencereader/sequences/invalid"


class TestSequenceReaderInitAndCheck(object):

    @pytest.mark.parametrize("seq_name",
                             os.listdir(VALID_SEQ_PATH))
    def test_valid_sequence(self, schema_path, seq_name):
        """Test the initialization of a valid sequence.

        No exception must be raised.
        """
        seq_path = os.path.join(VALID_SEQ_PATH, seq_name)
        SequenceReader(seq_path, schema_path)

    @pytest.mark.parametrize("seq_name",
                             os.listdir(INVALID_SEQ_PATH))
    def test_invalid_sequence(self, schema_path, seq_name):
        """Test the initialization of an invalid sequence.

        SequenceFileError exception must be raised.
        """
        seq_path = os.path.join(INVALID_SEQ_PATH, seq_name)
        with pytest.raises(SequenceFileError):
            SequenceReader(seq_path, schema_path)


class TestSequenceReaderParsing(object):

    def test_node_objects(self, schema_path):
        """Test instantiation of node objects."""
        seq_path = os.path.join(VALID_SEQ_PATH, "complexity_6.yaml")
        reader = SequenceReader(seq_path, schema_path)
        node_dict = reader.get_node_dict()

        # Check all the nodes
        n = node_dict[0]
        assert type(n) == StartNode
        assert n.nid == 0
        assert n.name == "start node"
        assert n.get_all_next_node_ids() == {2}

        n = node_dict[1]
        assert type(n) == StopNode
        assert n.nid == 1
        assert n.name == "stop node"

        n = node_dict[2]
        assert type(n) == FunctionNode
        assert n.nid == 2
        assert n.name == "Dummy node function"
        assert n.function_name == "dummy_function"
        assert n.return_var_name == 'spam'
        assert n.get_all_next_node_ids() == {5}
        assert n.wrapper_names == {"WrapperSpam", "WrapperEgg"}

        n = node_dict[5]
        assert type(n) == ParallelSplitNode
        assert n.nid == 5
        assert n.name == "A parallel splitter node"
        assert n.get_all_next_node_ids() == {3, 4}

        n = node_dict[6]
        assert type(n) == ParallelSyncNode
        assert n.nid == 6
        assert n.name == "A parallel synchronizer node"
        assert n.get_all_next_node_ids() == {1}

        n = node_dict[7]
        assert type(n) == VariableNode
        assert n.nid == 7
        assert n.get_all_next_node_ids() == {6}
        assert n.variables == {'a': 1, 'b': 2}

    def test_get_node_function_names(self, schema_path):
        """Test SequenceReader.get_node_function_names."""
        seq_path = os.path.join(VALID_SEQ_PATH, "complexity_6.yaml")
        reader = SequenceReader(seq_path, schema_path)
        func_names = reader.get_node_function_names()
        assert func_names == {'dummy_function',
                              'spam_function',
                              'egg_function'}

    def test_get_start_node_ids(self, schema_path):
        """Test SequenceReader.get_start_node_ids."""
        seq_path = os.path.join(VALID_SEQ_PATH, "complexity_6.yaml")
        reader = SequenceReader(seq_path, schema_path)
        start_nids = reader.get_start_node_ids()
        assert start_nids == {0, 8}

    def test_get_prev_node_ids(self, schema_path):
        """Test SequenceReader.get_prev_node_ids."""
        seq_path = os.path.join(VALID_SEQ_PATH, "complexity_6.yaml")
        reader = SequenceReader(seq_path, schema_path)
        prev_nids = reader.get_prev_node_ids(6)
        assert prev_nids == {3, 7}

    def test_get_constants(self, schema_path):
        """Test SequenceReader.get_prev_node_ids."""
        seq_path = os.path.join(VALID_SEQ_PATH, "complexity_6.yaml")
        reader = SequenceReader(seq_path, schema_path)
        constants = reader.get_constants()
        assert constants == {'name': 'complexity 6',
                             "one": 1,
                             "bool": True}

    def test_get_node_wrapper_names(self, schema_path):
        """Test SequenceReader.get_node_wrapper_names."""
        seq_path = os.path.join(VALID_SEQ_PATH, "complexity_6.yaml")
        reader = SequenceReader(seq_path, schema_path)
        names = reader.get_node_wrapper_names()
        assert names == {"WrapperSpam", "WrapperEgg", "WrapperFoo",
                         "WrapperBar"}

