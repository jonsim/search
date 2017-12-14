#!/usr/bin/env python
# (c) Copyright 2017 Jonathan Simmonds
"""search_modules module definition"""
import inspect
import pkgutil

class SearchModule(object):
    def __init__(self, name):
        self.name = name
        self.version = None
        self.search_func = None
        self.args_func = None

    def search(self, path):
        raise NotImplementedError()

    def __str__(self):
        return '%s %s' % (self.name, self.version) if self.version else self.name

modules = []
# Loop through all modules in this directory and create a SearchModule object
# # from them (i.e. treat everything here implicitly as a search module).
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    py_module = loader.find_module(module_name).load_module(module_name)
    search_module = SearchModule(module_name)
    for name, value in inspect.getmembers(py_module):
        if name == '__version__':
            search_module.version = value
        elif name == 'search':
            search_module.search_func = value
        elif name == 'parse_args':
            search_module.args_func = value
    modules.append(search_module)

__all__ = ['SearchModule', 'modules']
