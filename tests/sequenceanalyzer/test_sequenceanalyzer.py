#!/usr/bin/env python
# coding: utf-8

import pytest
import os

from yapyseq.sequenceanalyzer import *


class TestSequenceAnalyzerInitAndCheck(object):

    @pytest.mark.parametrize("seq_name", [
        "valid/minimal.yaml",
        "valid/minimal_with_optional.yaml"
    ])
    def test_valid_sequence(self, schema_path, seq_dir, seq_name):
        seq_path = os.path.join(seq_dir, seq_name)
        sa = SequenceAnalyzer(seq_path, schema_path)
