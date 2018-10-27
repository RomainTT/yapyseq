#!/usr/bin/env python
# coding: utf-8

import pytest


@pytest.fixture
def seq_dir():
    return "tests/sequencerunner/sequences/"


@pytest.fixture
def func_dir():
    return "tests/sequencerunner/functions/"


@pytest.fixture
def schema_path():
    return "yapyseq/seq_schema.yaml"
