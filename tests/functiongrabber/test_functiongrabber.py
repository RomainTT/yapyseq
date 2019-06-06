#!/usr/bin/env python
# coding: utf-8

import pytest
from yapyseq.functiongrabber import FunctionGrabber, \
    ItemExistenceError, ItemUniquenessError, UnknownItem


class TestSearchItemsInFile(object):

    def test_search_functions_in_file(self, func_dir):
        fg = FunctionGrabber()
        file_path = "{}/file1.py".format(func_dir)
        functions = {"function_1_1", "function_1_2", "function_foo"}
        ret = fg._search_items_in_file(file_path, functions, "function")
        assert ret == {"function_1_1", "function_1_2"}

    def test_search_wrappers_in_file(self, func_dir):
        fg = FunctionGrabber()
        file_path = "{}/file1.py".format(func_dir)
        wrappers = {"WrapperOneOne", "WrapperOneTwo", "WrapperFoo"}
        ret = fg._search_items_in_file(file_path, wrappers, "class")
        assert ret == {"WrapperOneOne", "WrapperOneTwo"}

    def test_search_items_in_file_empty(self, func_dir):
        fg = FunctionGrabber()
        file_path = "{}/file2.py".format(func_dir)
        functions = {"function_1_1", "function_1_2", "function_foo"}
        ret = fg._search_items_in_file(file_path, functions, "function")
        assert ret == set()

    def test_search_items_in_file_nonexistent(self, func_dir):
        fg = FunctionGrabber()
        file_path = "nonexistent_file.py".format(func_dir)
        functions = set()
        with pytest.raises(FileNotFoundError):
            ret = fg._search_items_in_file(file_path, functions, "function")


class TestImportFunctions(object):

    def test_import_functions(self, func_dir):
        fg = FunctionGrabber()
        functions = {"function_1_1", "function_1_2",
                     "function_2_1", "function_2_2"}
        fg.import_functions(func_dir, functions)
        assert len(fg._imported_functions) == 4

    def test_import_functions_nonexistent_dir(self):
        fg = FunctionGrabber()
        functions = set()
        directory = "nonexistent_directory"
        with pytest.raises(NotADirectoryError):
            fg.import_functions(directory, functions)

    def test_import_functions_not_dir(self, func_dir):
        fg = FunctionGrabber()
        functions = set()
        directory = "{}/file1.py".format(func_dir)
        with pytest.raises(NotADirectoryError):
            fg.import_functions(directory, functions)

    def test_import_functions_nonunique_func(self, func_dir):
        fg = FunctionGrabber()
        functions = {'function_redundant'}
        with pytest.raises(ItemUniquenessError):
            fg.import_functions(func_dir, functions)

    def test_import_functions_nonexistent_func(self, func_dir):
        fg = FunctionGrabber()
        functions = {'function_which_does_not_exist'}
        with pytest.raises(ItemExistenceError):
            fg.import_functions(func_dir, functions)


class TestGetFunction(object):

    def test_get_function(self, func_dir):
        fg = FunctionGrabber()
        functions = {"function_1_1"}
        fg.import_functions(func_dir, functions)
        f = fg.get_function("function_1_1")
        assert f() == "This is function_1_1."

    def test_get_function_unknown_func(self):
        fg = FunctionGrabber()
        with pytest.raises(UnknownItem):
            f = fg.get_function("foo")


class TestImportWrappers(object):

    def test_import_wrappers(self, func_dir):
        fg = FunctionGrabber()
        wrappers = {"WrapperOneOne", "WrapperOneTwo",
                     "WrapperTwoOne", "WrapperTwoTwo"}
        fg.import_wrappers(func_dir, wrappers)
        assert len(fg._imported_wrappers) == 4

    def test_import_wrappers_nonexistent_dir(self):
        fg = FunctionGrabber()
        wrappers = set()
        directory = "nonexistent_directory"
        with pytest.raises(NotADirectoryError):
            fg.import_wrappers(directory, wrappers)

    def test_import_wrappers_not_dir(self, func_dir):
        fg = FunctionGrabber()
        wrappers = set()
        directory = "{}/file1.py".format(func_dir)
        with pytest.raises(NotADirectoryError):
            fg.import_wrappers(directory, wrappers)

    def test_import_wrappers_nonunique_wrap(self, func_dir):
        fg = FunctionGrabber()
        wrappers = {'WrapperRedundant'}
        with pytest.raises(ItemUniquenessError):
            fg.import_wrappers(func_dir, wrappers)

    def test_import_wrappers_nonexistent_wrap(self, func_dir):
        fg = FunctionGrabber()
        wrappers = {'wrapper_which_does_not_exist'}
        with pytest.raises(ItemExistenceError):
            fg.import_wrappers(func_dir, wrappers)


class TestGetWrapper(object):

    def test_get_wrappers(self, func_dir):
        fg = FunctionGrabber()
        wrappers = {"WrapperOneOne"}
        fg.import_wrappers(func_dir, wrappers)
        wrap = fg.get_wrappers(wrappers)
        assert wrap["WrapperOneOne"].wraptest() == "This is WrapperOneOne."

    def test_get_wrappers_unknown_wrap(self):
        fg = FunctionGrabber()
        with pytest.raises(UnknownItem):
            wrap = fg.get_wrappers({"foo"})
