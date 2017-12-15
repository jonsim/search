#!/usr/bin/env python
# (c) Copyright 2017 Jonathan Simmonds
"""search_modules module definition"""
import inspect  # getmembers
import pkgutil  # walk_packages

class SearchModule(object):
    def __init__(self, name):
        self.name = name
        self.version = None
        self._search_func = None
        self._subparser_func = None
        self.subparser = None

    def validate(self):
        if not self._search_func:
            raise NotImplementedError('%s module lacks search function'
                                      % (self.name))
        if not self._subparser_func:
            raise NotImplementedError('%s module lacks subparser function'
                                      % (self.name))

    def get_subparser(self, subparsers):
        # Get the subparser from the wrapped module.
        self.subparser = self._subparser_func(subparsers)
        # Fill in the module parts.
        self.subparser.prog = self.name
        self.subparser.description = None
        self.subparser.epilog = None
        self.subparser.search_module = self
        return self.subparser

    def search(self, regex, paths, command_args, ignore_case=False, verbose=False):
        return self._search_func(regex, paths, command_args, ignore_case, verbose)

    def __str__(self):
        return '%s %s' % (self.name, self.version) if self.version else self.name

modules = []
# Loop through all modules in this directory and create a SearchModule object
# # from them (i.e. treat everything here implicitly as a search module).
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    py_module = loader.find_module(module_name).load_module(module_name)
    search_module = SearchModule(module_name)
    for member_name, value in inspect.getmembers(py_module):
        if member_name == '__version__':
            search_module.version = value
        elif member_name == 'search':
            search_module._search_func = value
        elif member_name == 'get_subparser':
            search_module._subparser_func = value
    search_module.validate()
    modules.append(search_module)

__all__ = ['SearchModule', 'modules']
