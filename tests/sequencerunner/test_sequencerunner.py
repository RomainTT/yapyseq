#!/usr/bin/env python
# coding: utf-8

import pytest
import os
from yapyseq.sequencerunner import *
from yapyseq.nodes import NodeFunctionTimeout, NodeWrapperPreError, \
                          NodeWrapperInitError, NodeWrapperPostError


class TestSequenceRunner(object):

    def test_user_constants(self, func_dir, seq_dir):
        """Check that constants written in sequence file are correctly stored
           as sequence variables.
        """
        sequence = os.path.join(seq_dir, "one_function_node.yaml")
        constants = {'spam': 'egg'}
        runner = SequenceRunner(sequence, func_dir, constants, logger=False)
        assert runner.variables['spam'] == 'egg'

    def test_one_function_node(self, func_dir, seq_dir):
        """Check that a sequence with a single function node is running
           correctly.
        """
        sequence = os.path.join(seq_dir, "one_function_node.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        node_result = runner.variables['results'][1]
        assert node_result.nid == 1
        assert node_result.exception is None
        assert node_result.returned == "Hello world!"

    def test_multiple_variable_nodes(self, func_dir, seq_dir):
        """Check that variable nodes correctly update the sequence variables."""
        sequence = os.path.join(seq_dir, "multiple_variable_nodes.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        variables = runner.variables
        assert variables['spam'] == 'egg'
        assert variables['none'] is None
        assert variables['number'] == 2
        assert variables['statement'] is True

    def test_readonly(self, func_dir, seq_dir):
        """Check that a constant cannot be updated in the sequence."""
        sequence = os.path.join(seq_dir, "readonly.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        with pytest.raises(ReadOnlyError):
            runner.run()

    def test_timeout(self, func_dir, seq_dir):
        """Test the timeout feature of function nodes."""
        sequence = os.path.join(seq_dir, "timeout.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        results = runner.variables['results']
        assert results[1].exception is not None
        assert type(results[1].exception.function) is NodeFunctionTimeout
        assert results[2].exception is None

    def test_conditional_transitions(self, func_dir, seq_dir):
        sequence = os.path.join(seq_dir, "multiple_function_nodes.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
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
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        results = runner.variables['results']
        assert all(nid in results for nid in nid_range)
        for nid in range(*nid_range):
            assert results[nid].returned < results[nid + 1].returned

    def test_simple_loop(self, func_dir, seq_dir):
        """Check that a simple loop can be achieved."""
        result_file = "tests/sequencerunner/loop_file.txt"
        sequence = os.path.join(seq_dir, "simple_loop.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        # Check the output file
        with open(result_file, 'r') as f:
            lines = f.readlines()
        os.remove(result_file)
        lines = [l.strip('\n') for l in lines]
        # Lines should contain numbers from 1 to 10
        for i in range(1, 11):
            assert lines.pop() == str(i)

    def test_return_variable(self, func_dir, seq_dir):
        """Check that the 'return' attribute of a function node works"""
        sequence = os.path.join(seq_dir, "return_variable.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        spam = runner.variables['spam']
        assert spam == "Hello world!"

    def test_wrappers(self, func_dir, seq_dir):
        """Check functionality of wrappers in function nodes."""
        sequence = os.path.join(seq_dir, "wrappers.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        # Check the run of post()
        result_file = "tests/sequencerunner/wrap.txt"
        with open(result_file, "r") as f:
            content = f.read()
        os.remove(result_file)
        assert content == "egg"
        # Check the run of pre()
        assert runner.variables["results"][1].returned == "foo"
        # Check use of wrapper argument among wrappers
        assert runner.variables["results"][2].returned == "FOO"

    def test_wrappers_exception(self, func_dir, seq_dir):
        """Check that exceptions are correctly saved from wrappers."""
        sequence = os.path.join(seq_dir, "wrapper_exceptions.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        runner.run()
        assert isinstance(runner.variables["results"][1].exception.wrappers,
                          NodeWrapperInitError)
        assert isinstance(runner.variables["results"][2].exception.wrappers,
                          NodeWrapperPreError)
        assert isinstance(runner.variables["results"][3].exception.wrappers,
                          NodeWrapperPostError)
        assert isinstance(runner.variables["results"][
                          1].exception.wrappers.cause,
                          RuntimeError)

    def test_function_tests(self, func_dir, seq_dir):
        """Check that is_test attribute is correctly managed."""
        sequence = os.path.join(seq_dir, "test_nodes.yaml")
        runner = SequenceRunner(sequence, func_dir, logger=False)
        with pytest.raises(TestSequenceFailed):
            runner.run()
