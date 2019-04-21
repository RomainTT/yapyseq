#!/usr/bin/env python
# coding: utf-8

from yapyseq import NodeWrapper


class WrapperSetFoo(NodeWrapper):
    def pre(self):
        return "foo"


class WrapperToCaps(NodeWrapper):
    def __init__(self, text):
        self.text = text
    def pre(self):
        return self.text.upper()


class WrapperWriteInFile(NodeWrapper):
    def __init__(self, filepath):
        self.filepath = filepath
    def post(self):
        with open(self.filepath, "w") as f:
            f.write("egg")


class WrapperExcInit(NodeWrapper):
    def __init__(self):
        raise RuntimeError


class WrapperExcPre(NodeWrapper):
    def pre(self):
        raise RuntimeError


class WrapperExcPost(NodeWrapper):
    def post(self):
        raise RuntimeError
