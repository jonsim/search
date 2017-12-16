# (c) Copyright 2017 Jonathan Simmonds
"""Search module for searching file contents.

This will ignore .git and .svn directories.
"""
import subprocess

# Module version
__version__ = '1.0'

def grep(regex, paths, ignore_case):
    # r (recursive), n (print line num), s (no error messages), H (print filename),
    # Z (NUL terminate filenames), I (ignore binary files), P (Perl regex)
    grep_args = '-rnsHZIP'
    if ignore_case:
        grep_args += 'i'
    try:
        return subprocess.check_output(['grep', '--color=never', grep_args,
                                        '--exclude-dir=".svn"',
                                        '--exclude-dir=".git"', regex] + paths).strip()
    except subprocess.CalledProcessError as cpe:
        if cpe.returncode == 1:
            return ''
        else:
            raise

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
    results = grep(regex, paths, ignore_case)
    # TODO prettify output
    if results:
        print results

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
