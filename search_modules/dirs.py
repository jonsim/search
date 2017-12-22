# Copyright (c) 2017 Jonathan Simmonds
"""Search module for searching directory contents.

This will ignore .git and .svn directories.
"""
import os
import re
from search_utils.printer import MultiLinePrinter
from search_utils.result import SearchResult, StringMatch

# Module version.
__version__ = '1.0'

# Ignored directory names.
IGNORED_DIRS = ['.git', '.svn']

def search_generator(regex, paths, ignore_case, path_regex):
    """Generator method for search results.

    Args:
        regex:          String regular expression to search with.
        paths:          List of strings representing the paths to search.
        ignore_case:    Boolean, True if the search should be case-insensitive,
            False if it should be case-sensitive.
        path_regex:     Boolean, True if the search regex should be applied to
            the entire path or just the file/directory name.
    """
    re_flags = re.IGNORECASE if ignore_case else 0
    for path in paths:
        for dirname, subdirs, files in os.walk(path):
            # Don't recurse into any of the ignored subdirectories.
            for ignored_dir in IGNORED_DIRS:
                if ignored_dir in subdirs:
                    subdirs.remove(ignored_dir)
            # Match against all remaining files and subdirs in the directory.
            for node_name in subdirs + files:
                node_path = os.path.join(dirname, node_name)
                if re.search(regex, node_path if path_regex else node_name,
                             flags=re_flags):
                    yield SearchResult(StringMatch(node_path, regex, ignore_case))

def search(regex, paths, args, ignore_case=False, verbose=False):
    """Perform the requested search.

    Args:
        regex:          String regular expression to search with.
        paths:          List of strings representing the paths to search in/on.
        args:           Namespace containing all parsed arguments. If the
            subparser added additional arguments these will be present.
        ignore_case:    Boolean, True if the search should be case-insensitive,
            False if it should be case-sensitive.
        verbose:        Boolean, True for verbose output, False otherwise.
    """
    path_regex = os.path.sep in regex
    printer = MultiLinePrinter()
    printer.print_results(search_generator(regex, paths, ignore_case, path_regex))

def create_subparser(subparsers):
    """Creates this module's subparser.

    Args:
        subparsers: Special handle object (argparse._SubParsersAction) which can
            be used to add subparsers to a parser.

    Returns:
        Object representing the created subparser.
    """
    parser = subparsers.add_parser(
        'dirs',
        add_help=False,
        help='Search recursively on the file names of any files in the given '
             'paths.')
    return parser
