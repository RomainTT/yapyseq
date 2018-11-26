#!/usr/bin/env python
# coding: utf-8

import pytest
import os

from yapyseq.sequencerunner import *
from yapyseq.nodes import NodeFunctionTimeout


class TestSequenceRunner(object):

    def test_user_constants(self, func_dir, seq_dir):
        """Check that constants written in sequence file are correctly stored
           as sequence variables.
        """
        sequence = os.path.join(seq_dir, "one_function_node.yaml")
        constants = {'spam': 'egg'}
        runner = SequenceRunner(sequence, func_dir, constants)
        assert runner.variables['spam'] == 'egg'

    def test_one_function_node(self, func_dir, seq_dir):
        """Check that a sequence with a single function node is running
           correctly.
        """
        sequence = os.path.join(seq_dir, "one_function_node.yaml")
        runner = SequenceRunner(sequence, func_dir)
        runner.run()
        node_result = runner.variables['results'][1]
        assert node_result.nid == 1
        assert node_result.exception.is_raised is False
        assert node_result.returned == "Hello world!"

    def test_multiple_variable_nodes(self, func_dir, seq_dir):
        """Check that variable nodes correctly update the sequence variables."""
        sequence = os.path.join(seq_dir, "multiple_variable_nodes.yaml")
        runner = SequenceRunner(sequence, func_dir)
        runner.run()
        variables = runner.variables
        assert variables['spam'] == 'egg'
        assert variables['none'] is None
        assert variables['number'] == 2
        assert variables['statement'] is True

    def test_readonly(self, func_dir, seq_dir):
        """Check that a constant cannot be updated in the sequence."""
        sequence = os.path.join(seq_dir, "readonly.yaml")
        runner = SequenceRunner(sequence, func_dir)
        with pytest.raises(ReadOnlyError):
            runner.run()

    def test_timeout(self, func_dir, seq_dir):
        """Test the timeout feature of function nodes."""
        sequence = os.path.join(seq_dir, "timeout.yaml")
        runner = SequenceRunner(sequence, func_dir)
        runner.run()
        results = runner.variables['results']
        assert results[1].exception.is_raised is True
        assert type(results[1].exception.object) is NodeFunctionTimeout
        assert results[2].exception.is_raised is False

    def test_conditional_transitions(self, func_dir, seq_dir):
        sequence = os.path.join(seq_dir, "multiple_function_nodes.yaml")
        runner = SequenceRunner(sequence, func_dir)
        runner.run()
        results = runner.variables['results']
        assert all(nid in results for nid in [1, 2, 3])
        for nid in range(1, 3):
            assert results[nid] < results[nid + 1]

    @pytest.mark.parametrize("seq_file,nid_range",
                             [("multiple_function_nodes.yaml", (1, 3)),
                              ("simple_parallel.yaml", (2, 5)),
                              ("multiple_parallel.yaml", (2, 6))])
    def test_execution_order(self, func_dir, seq_dir, seq_file, nid_range):
        """Check that a sequence is running in the right order."""
        sequence = os.path.join(seq_dir, seq_file)
        runner = SequenceRunner(sequence, func_dir)
        runner.run()
        results = runner.variables['results']
        assert all(nid in results for nid in nid_range)
        for nid in range(*nid_range):
            assert results[nid].returned < results[nid + 1].returned

    def test_simple_loop(self, func_dir, seq_dir):
        """Check that a simple loop can be achieved."""
        result_file = "tests/sequencerunner/loop_file.txt"
        sequence = os.path.join(seq_dir, "simple_loop.yaml")
        runner = SequenceRunner(sequence, func_dir)
        runner.run()
        # Check the output file
        with open(result_file, 'r') as f:
            lines = f.readlines()
        os.remove(result_file)
        lines = [l.strip('\n') for l in lines]
        # Lines should contain numbers from 1 to 10
        for i in range(1, 11):
            assert lines.pop() == str(i)
