#!/usr/bin/env python
# coding: utf-8
"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import abc
from typing import Dict, Any

# ------------------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------------------

class YapyseqInternalError(RuntimeError):
    """An exception for errors not related to user content."""

# ------------------------------------------------------------------------------
# Common functions
# ------------------------------------------------------------------------------

def evaluate_expr(expr: Any, variables: Dict = None) -> Any:
    """Evaluate a Python expression if it is recognized as one.

    Args:
        expr: a string with a Python expression
          or a directly a Python object if not an expression.
        variables: dictionary of variable_name:variable_value taken as local
            variables while evaluating the expression (arg of eval()).

    Returns:
        The value of the evaluated expression, or the object itself if it is
        not an expression.
    """
    if variables is None:
        variables = {}
    if type(expr) is str:
        # None is given as globals and variables are given as locals
        value = eval(expr, None, variables)
    else:
        # If the expression is not an expression but directly
        # a value, do not evaluate it.
        value = expr
    return value


def evaluate_kwargs(kwargs_dict: Dict, variables: Dict = None) -> Dict:
    """Evaluate values of a dictionary.

    Args:
        kwargs_dict: dictionary of to evaluate. If a value is a string, it will
            evaluated as a Python expression. Therefore, to get actual strings
            one must use quotes.
        variables: (optional) dictionary of variables to take into account
            while evaluating the Python expressions.

    Returns:
        A dictionary similar to kwargs_dict but after evaluation of
        expressions.
    """
    evaluated_kwargs = {}
    for arg_name, arg_value in kwargs_dict.items():
        evaluated_kwargs[arg_name] = evaluate_expr(arg_value, variables)
    return evaluated_kwargs


# ------------------------------------------------------------------------------
# Common classes
# ------------------------------------------------------------------------------

class NodeWrapper(abc.ABC):
    """Parent class used to create node wrappers.

    This class must be imported and used by user.
    """
    def pre(self):
        pass
    def post(self):
        pass
