#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Callable, Set, Dict, List
import os
import sys
from importlib import import_module
import mmap
import re


# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------


class ItemUniquenessError(ImportError):
    pass


class ItemExistenceError(ImportError):
    pass


class UnknownItem(ValueError):
    pass


class WrapperTypeError(ImportError):
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
        self._imported_wrappers = dict()

    @staticmethod
    def _search_items_in_file(file_path: str, item_set: Set, item_type: str) -> Set:
        """Search for a list of items in a python file.

        Only first level items are searched. It means they must be contained
        in the file itself, and not nested in a class or in a function.

        Warning:
            Only works on utf-8 encoded files.

        Args:
            file_path: Path to the .py file where items must be searched.
            func_set: The names of the items to search for.
            item_type: The type of the items to search. Whether "class" or
                "function".

        Returns:
            The set of matching functions found in the file.
            Empty set if none.

        Raises:
            FileNotFoundError: if file_path lead to no real file.
            OSError: if file cannot be read.
            ValueError: if item_type is unknown
        """
        if item_type == "function":
            type_pattern = "def"
        elif item_type == "class":
            type_pattern = "class"
        else:
            raise ValueError("Unknown item_type")
        if not os.path.isfile(file_path):
            raise FileNotFoundError("No file can be found at"
                                    " {}".format(file_path))

        # Create a REGEX pattern to find all items in the files
        # This pattern contains all the item names, it will be like
        # this: "def (func1|func2|func3|)\s*\("
        # It must be used with re.findall()
        spattern = r"^{} (".format(type_pattern)
        for item in item_set:
            spattern = spattern + "{}|".format(item)
        spattern = spattern + r")\s*\("
        # pattern must be given in bytes because mmap read bytes
        bpattern = bytes(spattern, "utf-8")  # files are utf-8

        with open(file_path, 'rb', 0) as f:
            # To know why mmap is used, read
            # https://stackoverflow.com/questions/258091/when-should-i-use-mmap-for-file-access
            # https://stackoverflow.com/questions/25268465/using-mmap-to-apply-regexp-to-whole-file-in-python
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mfile:
                # Find all functions from the set in one shot
                found_items = re.findall(bpattern, mfile, re.MULTILINE)

        # Decode binary strings into utf-8
        found_items = [f.decode('utf-8') for f in found_items]

        return set(found_items)

    def _import_items(self, directory: str, item_set: Set, item_type: str) -> Dict:
        """Search for items in a directory and import them.

        Search is recursive, starting on given directory as top.
        Only necessary items are imported. Modules required by python files
        containing these items will also be imported, following the
        classical import management of Python.

        Args:
            directory: The directory in which items must be searched for.
                Only the files contained in this directory and its sub-directories
                (search is recursive) can be imported.
            func_set: The names of the items to import.
            item_type: The type of the items to import. Wether "function" or
                "class".

        Returns:
            Dictionary of imported items.

        Raises:
            NotADirectoryError: if the given directory does not exist.
            ImportError: if a problem occurred during the importation of one of
                the functions.
            ItemUniquenessError: if a function has been found several times.
            ItemExistenceError: if a function has not been found at all.
        """
        # Check the existence of the directory to search in
        if not os.path.isdir(directory):
            raise NotADirectoryError(
                "The directory {} does not exist.".format(directory))

        # Create a dict to store a counter for each item in the list
        # Each counter counts the number of time an item has been found
        # All counters are initialized to zero before the search begins
        # Counters will serve to check uniqueness of items
        counter_dict = dict([(i, 0) for i in item_set])

        # Create a dict that contains Python files to import for each function
        # In other words, it contains the location of each function
        location_dict = dict([(i, None) for i in item_set])

        # For every Python file that is found, search for items
        # and save their location.
        for (path, dir_list, file_list) in os.walk(directory):
            for file_name in file_list:
                if file_name.endswith(".py"):
                    file_path = os.path.join(path, file_name)
                    # Search for items in this file
                    found_items = self._search_items_in_file(file_path,
                                                            item_set,
                                                            item_type)
                    for item_name in found_items:
                        # Update the counter
                        counter_dict[item_name] += 1
                        # Save location
                        location_dict[item_name] = file_path

        # Check uniqueness of all items
        non_unique_items = [i for i in item_set if counter_dict[i] > 1]
        if len(non_unique_items):
            raise ItemUniquenessError(("Following items are not unique"
                                       " : {}".format(non_unique_items)))

        # Check that all items have been found
        not_found_items = [i for i in item_set if counter_dict[i] == 0]
        if len(not_found_items):
            raise ItemExistenceError(("Following items have not been "
                                      "found: {}".format(not_found_items)))

        # Import items
        imported_items = {}
        for item_name in item_set:
            # Decompose the path
            file_path = location_dict[item_name]
            file_dir, file_name = os.path.split(file_path)
            file_name_no_ext, ext = os.path.splitext(file_name)

            # Add file directory to the path
            sys.path.append(file_dir)

            # Import the item
            try:
                mod = import_module(file_name_no_ext)
                imported_item = getattr(mod, item_name)
            except ImportError as exc:
                raise ImportError(("Error while trying to import the following"
                                   " item: {}").format(item_name)) from exc
            imported_items[item_name] = imported_item

        return imported_items

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
            Same than _import_items()
        """
        self._imported_functions = self._import_items(directory, func_set,
                                                      "function")

    def import_wrappers(self, directory: str, wrapper_set: Set) -> None:
        """Search for wrappers in a directory and import them.

        Search is recursive, starting on given directory as top.
        Only necessary classes are imported. Modules required by python files
        containing these functions will also be imported, following the
        classical import management of Python.

        Args:
            directory: The directory in which functions must be searched for.
              Only the files contained in this directory and its sub-directories
              (search is recursive) can be imported.
            wrapper_set: Names of wrappers to import.

        Raises:
            Same than _import_items()
        """
        # TODO: check that wrappers are subclasse of NodeWrapper
        # imported_wrappers = self._import_items(directory, wrapper_set, "class")
        # for wrapper in imported_wrappers:
            # if not issubclass(wrapper, NodeWrapper):
                # raise BadWrapperClass(…)

        self._imported_wrappers = self._import_items(directory, wrapper_set,
                                                     "class")

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
            raise UnknownItem(("Following function is unknown, it has not "
                               "been imported yet: {}".format(func_name)))
        return self._imported_functions[func_name]

    def get_wrappers(self, wrapper_names: Set) -> Dict:
        """Get wrapper classes according to the given name list.

        Args:
            wrapper_names: list of wrapper names to get their classes.

        Returns:
            A dictionary where keys are wrapper names and values are references
            to classes.
        """
        if any(name not in self._imported_wrappers for name in wrapper_names):
            raise UnknownItem('On of the required wrappers has not been '
                              'imported.')
        return {k:v for k, v in self._imported_wrappers.items() if k in
                wrapper_names}
