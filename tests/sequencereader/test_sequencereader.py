#!/usr/bin/env python
# coding: utf-8

import pytest
import os

from yapyseq.sequencereader import *

VALID_SEQ_PATH = "tests/sequencereader/sequences/valid"
INVALID_SEQ_PATH = "tests/sequencereader/sequences/invalid"


class TestSequenceAnalyzerInitAndCheck(object):

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
        """Test the initialization of a valid sequence.

        No exception must be raised.
        """
        seq_path = os.path.join(INVALID_SEQ_PATH, seq_name)
        with pytest.raises(SequenceFileError):
            SequenceReader(seq_path, schema_path)
