#!/usr/bin/env python
# coding: utf-8


class FunctionUniquenessError(ImportError):
    pass


class FunctionExistenceError(ImportError):
    pass


class UnknownFunction(FunctionExistenceError):
    pass


class SequenceFileError(ValueError):
    pass
