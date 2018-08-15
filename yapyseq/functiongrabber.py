#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from types import FunctionType
import os
import mmap
import re
from .exceptions import *


class FunctionGrabber(object):
    """Class to get access to functions of a specific directory.

    The aim of an instance of `FunctionGrabber` is:
        * to import the python files containing the functions that can be
          executed in a given sequence.
        * Provide these functions on demand through its API
    """
    def _search_functions_in_file(self, file_path: str,
                                  func_list: list) -> list:
        """Search for a list of functions in a python file.

        Only first level functions are searched. It means they must be contained
        in the file itself, and not nested in a class or in another function.
        Warning: Only works on utf-8 files.

        Args:
            file_path: Path to the .py file where functions must be searched.
            func_list: The list of functions to search for.

        Returns:
            The list of matching functions found in the file.
            Empty list if none.

        Raises:
            ValueError: if file_path lead to no real file.
        """
        if not os.path.isfile(file_path):
            raise ValueError("No file can be found at {}".format(file_path))

        # Initialize result as an empty list
        found_func = []

        with open(file_path, 'rb', 0) as f:
            # To know why mmap is used, read
            # https://stackoverflow.com/questions/258091/when-should-i-use-mmap-for-file-access
            # https://stackoverflow.com/questions/25268465/using-mmap-to-apply-regexp-to-whole-file-in-python
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mfile:
                # TODO: Find the best way to search for multiple functions in a file
                # Some timing tests must be done on large files.
                for func in func_list:
                    # pattern must be given in bytes because mmap read bytes
                    spattern = "^def {}\s*\(".format(func)  # create regex
                    bpattern = bytes(spattern, "utf-8")  # files are utf-8
                    if re.search(bpattern, mfile, re.MULTILINE):
                        # Function has been found, append it to result
                        found_func.append(func)
        return found_func

    def import_functions(self, directory: str, func_list: list):
        """Search for functions in a directory and import them.

        Search is recursive. Only necessary functions are imported, as well as
        their dependencies.

        Args:
            directory: The directory in which functions must be searched for.
              Only the files contained in this directory and its sub-directories
              (search is recursive) can be imported.
            func_list: The list of functions to import.
        """
        # Check the existence of the directory to search in
        if not os.path.isdir(directory):
            raise ValueError(
                "The directory {} does not exist.".format(directory))

        # Create a dict to store a counter for each function in the list
        # Each counter counts the number of time a function has been found
        # All counters are initialized to zero before the search begins
        # Counters will serve to check uniqueness of functions
        counter_dict = dict([(f, 0) for f in func_list])

        # Create a dict that contains Python files to import for each function
        # In other words, it contains the location of each function
        location_dict = dict([(f, None) for f in func_list])

        # For every Python file that is found, search for functions
        # and save their location.
        for (path, dir_list, file_list) in os.walk():
            for file_name in file_list:
                if file_name.endswith(".py"):
                    file_path = os.path.join(path, file_name)
                    # Search for functions in this file
                    found_func = self._search_functions_in_file(file_path,
                                                                func_list)
                    for func in found_func:
                        # Update the counter
                        counter_dict[func] += 1
                        # Save location
                        location_dict[func] = file_path

        # Check uniqueness of all functions
        non_unique_func = [func for func in func_list if counter_dict[func] > 1]
        if len(non_unique_func):
            raise FunctionUniquenessError("Following functions are not ",
                                          "unique : {}".format(non_unique_func))

        # Import functions
        # TODO

    def get_function(self, func_name: str) -> FunctionType:
        pass
