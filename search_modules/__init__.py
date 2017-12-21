# Copyright (c) 2017 Jonathan Simmonds
"""search_modules module definition"""
import inspect  # getmembers
import pkgutil  # walk_packages

class SearchModule(object):
    """Wrapper for each loaded search module.

    Attributes:
        name:       String name uniquely identifying this module from others.
            Not None.
        version:    String version identifier. May be None.
        subparser:  Object representing the subparser used by this module to
            contribute its switch and any additional options it permits. This
            object is that returned by argparser.subparser.add_parser().
    """
    def __init__(self, name):
        """Initialise the module.

        Args:
            name:   String name to uniquely identify the module. Not None.
        """
        self.name = name
        self.version = None
        self.subparser = None
        self._search_func = None
        self._subparser_func = None

    def validate(self):
        """Raise an exception if the module is misconfigured/incomplete."""
        if not self.name:
            raise Exception('Loaded module lacks name')
        if not self._search_func:
            raise NotImplementedError('%s module lacks search function'
                                      % (self.name))
        if not self._subparser_func:
            raise NotImplementedError('%s module lacks subparser function'
                                      % (self.name))

    def create_subparser(self, subparsers):
        """Creates and configures this module's subparser.

        After calling this method the subparser attribute will be accessible.

        Args:
            subparsers: Special handle object (argparse._SubParsersAction)
                which can be used to add subparsers to a parser.

        Returns:
            Object representing the created subparser.
        """
        # Get the subparser from the wrapped module.
        self.subparser = self._subparser_func(subparsers)
        if not self.subparser:
            raise Exception('%s module failed to return a subparser'
                            % (self.name))
        # Fill in the module parts.
        self.subparser.prog = self.name
        self.subparser.description = None
        self.subparser.epilog = None
        self.subparser.search_module = self
        # Set the search callback.
        self.subparser.set_defaults(search=self._search)
        return self.subparser

    def _search(self, args):
        """Search callback, intended to be called indirectly by the subparser.

        This will accept the parsed args and split them to be passed through to
        the module.
        """
        return self._search_func(args.regex, args.paths, args, args.ignore_case,
                                 args.verbose)

    def __str__(self):
        return '%s %s' % (self.name, self.version) if self.version else self.name

# Exported global to pass the loaded module list.
_search_modules = []
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
        elif member_name == 'create_subparser':
            search_module._subparser_func = value
    search_module.validate()
    _search_modules.append(search_module)

# Export the module class definition and the list of all loaded modules.
__all__ = ['SearchModule', '_search_modules']
