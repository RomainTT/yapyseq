#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging


def get_logger(name: str,
               level: int=logging.INFO,
               file_path: str=None,
               entry_format: str=None,
               disabled: bool=False):
    """Create and get a logging.Logger object with a single handler.

    Args:
        name: (str) the name of the logger to get with logging.getLogger
        level: (int) (optional) the level of logging.
            Default is logging.INFO.
        file_path: (str) (optional) A string being a path to a file to write
            logs in this file. Warning: this file will be overwritten if it
            already exists. None to display log in console (default).
        entry_format: (str) (optional) String being the format of the logs.
            If None (default) a default format will be used.
        disabled: (bool) (optional) Set to True to disable the logging. If a
            file path is given, it will still be created but with nothing
            inside. Default is False.

    Returns:
        A logging.Logger object, already configured.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if file_path:
        handler = logging.FileHandler(file_path)
    else:
        handler = logging.StreamHandler()

    if entry_format:
        formatter = logging.Formatter(entry_format)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    if disabled:
        logging.disable(logging.CRITICAL)

    return logger
