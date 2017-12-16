# (c) Copyright 2017 Jonathan Simmonds
"""Search module for searching file contents."""
__version__ = '1.0'

def search(regex, paths, command_args, ignore_case=False, verbose=False):
    """Perform the requested search.

    Args:
        regex:          String regular expression to search with.
        paths:          List of strings representing the paths to search in/on.
        command_args:   Namespace containing all parsed arguments. If the
            subparser added additional arguments these will be present.
        ignore_case:    Boolean, True if the search should be case-insensitive,
            False if it should be case-sensitive.
        verbose:        Boolean, True for verbose output, False otherwise.
    """
    print 'grep search_result'

def create_subparser(subparsers):
    """Creates this module's subparser.

    Args:
        subparsers: Special handle object (argparse._SubParsersAction) which can
            be used to add subparsers to a parser.

    Returns:
        Object representing the created subparser.
    """
    parser = subparsers.add_parser(
        'files',
        add_help=False,
        help='Search recursively on the contents of any files in the given '
             'paths.')
    #parser.add_argument('-r', action='store_const',
    #                    const=True, default=False,
    #                    help='Use ripgrep instead of grep')
    return parser
