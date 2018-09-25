#!/usr/bin/env python
# coding: utf-8

import pytest


@pytest.fixture
def seq_dir():
    return "tests/sequenceanalyzer/sequences/"


@pytest.fixture
def schema_path():
    return "yapyseq/seq_schema.yaml"
