#!/usr/bin/env python
# coding: utf-8

from yapyseq import NodeWrapper

def function_2_1():
    return "This is function_2_1."


def function_2_2():
    return "This is function_2_2."


def function_2_3():
    return "This is function_2_3."


def function_redundant():
    pass


class WrapperTwoOne(NodeWrapper):
    pass


class WrapperTwoTwo(NodeWrapper):
    pass


class WrapperRedundant(NodeWrapper):
    pass

