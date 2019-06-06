#!/usr/bin/env python
# coding: utf-8

from yapyseq import NodeWrapper

def function_1_1():
    return "This is function_1_1."


def function_1_2():
    return "This is function_1_2."


def function_1_3():
    return "This is function_1_3."


def function_redundant():
    pass


class WrapperOneOne(NodeWrapper):
    def wraptest():
        return "This is WrapperOneOne."


class WrapperOneTwo(NodeWrapper):
    pass


class WrapperRedundant(NodeWrapper):
    pass

