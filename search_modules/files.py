# (c) Copyright 2017 Jonathan Simmonds
"""Search module for searching file contents.

This will ignore .git and .svn directories.
"""
import sys
from search_utils.process import StreamingProcess
from search_utils.result import SearchResult, TextFileMatch, TextFileLocation
from search_utils.printer import BufferingTwoColumnPrinter

# Module version
__version__ = '1.0'

def search_result_from_grep(line, regex=None, ignore_case=False):
    """Creates a SearchResult object from the output from a grep command.

    NB: This relies on grep being called with at least args 'HIZns'

    Args:
        line:   String single line of grep output to process.
        regex:  String regex this result is derived from, or None if unknown.
            Defaults to None.

    Returns:
        The initialised SearchResult.
    """
    path_split = line.split('\0', 1)
    if len(path_split) != 2:
        raise Exception('Line does not look like grep -HIZns output: ' + line)
    line_split = path_split[1].split(':', 1)
    if len(line_split) != 2:
        raise Exception('Line does not look like grep -HIZns output: ' + line)
    return SearchResult(TextFileMatch(line_split[1].strip(), regex, ignore_case),
                        TextFileLocation(path_split[0], int(line_split[0])))

def grep(regex, paths, ignore_case, verbose):
    if sys.platform == 'linux':
        # Assume Linux has GNU grep. This has the options:
        # -r (recursive), -n (print line num), -s (no error messages),
        # -H (print filename), -Z (NUL terminate filenames),
        # -I (ignore binary files), -P (Perl regex)
        grep_args = ['-rnsHZIP']
    else:
        # Otherwise assume BSD grep. This has the options:
        # -r (recursive), -n (print line num), -s (no error messages),
        # -H (print filename), --null (NUL terminate filenames),
        # -I (ignore binary files), -E (extended regex)
        grep_args = ['-rnsHIE', '--null']
    if ignore_case:
        # GNU + BSD grep both have: i (ignore case)
        grep_args[0] += 'i'

    with StreamingProcess(['grep', '--color=never'] + grep_args +
                          ['--exclude-dir=.svn', '--exclude-dir=.git',
                           regex] + paths) as proc:
        # printer = SingleLinePrinter(condense_location=not verbose,
        #                             condense_match=not verbose)
        printer = BufferingTwoColumnPrinter(condense_location=not verbose,
                                            condense_match=not verbose)
        printer.print_results(search_result_from_grep(line, regex, ignore_case)
                              for line in proc)

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
    grep(regex, paths, ignore_case, verbose)

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
