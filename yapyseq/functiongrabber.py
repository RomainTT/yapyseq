#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Callable, Set
import os
import sys
from importlib import import_module
import mmap
import re


# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class FunctionUniquenessError(ImportError):
    pass


class FunctionExistenceError(ImportError):
    pass


class UnknownFunction(ValueError):
    pass


# ------------------------------------------------------------------------------
# Main class
# ------------------------------------------------------------------------------


class FunctionGrabber(object):
    """Class to get access to functions of a specific directory.

    The aim of an instance of `FunctionGrabber` is:
        * to import the python files containing the functions that can be
          executed in a given sequence.
        * Provide these functions on demand through its API

    Public attributes:
        None
    """

    # --------------------------------------------------------------------------
    # Private methods
    # --------------------------------------------------------------------------

    def __init__(self):
        self._imported_functions = dict()

    @staticmethod
    def _search_functions_in_file(file_path: str, func_set: Set) -> Set:
        """Search for a list of functions in a python file.

        Only first level functions are searched. It means they must be contained
        in the file itself, and not nested in a class or in another function.
        Warning: Only works on utf-8 files.

        Args:
            file_path: Path to the .py file where functions must be searched.
            func_set: The set of functions to search for.

        Returns:
            The set of matching functions found in the file.
            Empty set if none.

        Raises:
            FileNotFoundError: if file_path lead to no real file.
            OSError: if file cannot be read.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError("No file can be found at"
                                    " {}".format(file_path))

        # Create a REGEX pattern to find all functions in the files
        # This pattern contains all the function names, it will be like
        # this: "def (func1|func2|func3|)\s*\("
        # It must be used with re.findall()
        spattern = r"^def ("
        for func in func_set:
            spattern = spattern + "{}|".format(func)
        spattern = spattern + r")\s*\("
        # pattern must be given in bytes because mmap read bytes
        bpattern = bytes(spattern, "utf-8")  # files are utf-8

        with open(file_path, 'rb', 0) as f:
            # To know why mmap is used, read
            # https://stackoverflow.com/questions/258091/when-should-i-use-mmap-for-file-access
            # https://stackoverflow.com/questions/25268465/using-mmap-to-apply-regexp-to-whole-file-in-python
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mfile:
                # Find all functions from the set in one shot
                found_func = re.findall(bpattern, mfile, re.MULTILINE)

        # Decode binary strings into utf-8
        found_func = [f.decode('utf-8') for f in found_func]

        return set(found_func)

    # --------------------------------------------------------------------------
    # Public methods
    # --------------------------------------------------------------------------

    def import_functions(self, directory: str, func_set: Set) -> None:
        """Search for functions in a directory and import them.

        Search is recursive, starting on given directory as top.
        Only necessary functions are imported. Modules required by python files
        containing these functions will also be imported, following the
        classical import management of Python.

        Args:
            directory: The directory in which functions must be searched for.
              Only the files contained in this directory and its sub-directories
              (search is recursive) can be imported.
            func_set: The set of functions to import.

        Raises:
            NotADirectoryError: if the given directory does not exist.
            ImportError: if a problem occurred during the importation of one of
              the functions.
            FunctionUniquenessError: if a function has been found several times.
            FunctionExistenceError: if a function has not been found at all.
        """
        # Check the existence of the directory to search in
        if not os.path.isdir(directory):
            raise NotADirectoryError(
                "The directory {} does not exist.".format(directory))

        # Create a dict to store a counter for each function in the list
        # Each counter counts the number of time a function has been found
        # All counters are initialized to zero before the search begins
        # Counters will serve to check uniqueness of functions
        counter_dict = dict([(f, 0) for f in func_set])

        # Create a dict that contains Python files to import for each function
        # In other words, it contains the location of each function
        location_dict = dict([(f, None) for f in func_set])

        # For every Python file that is found, search for functions
        # and save their location.
        for (path, dir_list, file_list) in os.walk(directory):
            for file_name in file_list:
                if file_name.endswith(".py"):
                    file_path = os.path.join(path, file_name)
                    # Search for functions in this file
                    found_func = self._search_functions_in_file(file_path,
                                                                func_set)
                    for func_name in found_func:
                        # Update the counter
                        counter_dict[func_name] += 1
                        # Save location
                        location_dict[func_name] = file_path

        # Check uniqueness of all functions
        non_unique_func = [func for func in func_set if counter_dict[func] > 1]
        if len(non_unique_func):
            raise FunctionUniquenessError(("Following functions are not unique"
                                           " : {}".format(non_unique_func)))

        # Check that all functions have been found
        not_found_func = [func for func in func_set if counter_dict[func] == 0]
        if len(not_found_func):
            raise FunctionExistenceError(("Following functions have not been "
                                          "found: {}".format(not_found_func)))

        # Import functions
        for func_name in func_set:
            # Decompose the path
            file_path = location_dict[func_name]
            file_dir, file_name = os.path.split(file_path)
            file_name_no_ext, ext = os.path.splitext(file_name)

            # Add file directory to the path
            sys.path.append(file_dir)

            # Import the function
            try:
                mod = import_module(file_name_no_ext)
                imported_func = getattr(mod, func_name)
            except ImportError as e:
                raise ImportError(("Error while trying to import the following"
                                   " function: {}\nGot following error:\n",
                                   "{}".format(repr(e))))
            else:
                self._imported_functions[func_name] = imported_func

    def get_function(self, func_name: str) -> Callable:
        """Get the function object of a given function name, already imported

        Args:
            func_name: Name of the function to get. This function must have been
              imported previously, using import_functions().

        Returns:
            The function object of type Callable.

        Raises:
            UnknownFunction is the function has not been imported.
        """
        if func_name not in self._imported_functions:
            raise UnknownFunction(("Following function is unknown, it has not "
                                   "been imported yet: {}".format(func_name)))
        else:
            return self._imported_functions[func_name]
