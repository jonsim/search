 Table of Contents

- [search](#search)
  - [Dependencies](#dependencies)
  - [Installation](#installation)
  - [License](#license)
- [Documentation](#documentation)
  - [Usage](#usage)
  - [Examples](#examples)
  - [Modules](#modules)
    - [Adding a module](#adding-a-module)
    - [Writing a module](#writing-a-module)


# search
A general purpose, extensible search utility, written in Python.

Copyright &copy; 2017 Jonathan Simmonds


## Dependencies
* Python 2.6+

## Installation
Ensure the `search` file alongside this README is executable and run it.
Optionally place `search` on your system PATH.

## License
All files are licensed under the MIT license.

# Documentation
## Usage
```search -h
usage: search [-h] [--version] [dirs | files | symbols [-u]] [-i] [-v]
           [path [path ...]] regex

A module-based, recursive file searching utility.

positional arguments:
  path                  Optional path(s) to perform the search in or on. If
                        ommitted the current working directory is used.
  regex                 Perl-style regular expression to search for. It is
                        recommended to pass this in single quotes to prevent
                        shell expansion or interpretation of the regex
                        characters.

global arguments:
  -h, --help            Show this help message and exit.
  --version             Show the version number of the program and its
                        installed modules and exit.

search modules:
  {dirs,files,symbols}  Select which search module to use. Defaults to files.
    dirs                Search recursively on the file names of any files in
                        the given paths.
    files               Search recursively on the contents of any files in the
                        given paths.
    symbols             Search recursively in any object files or archives for
                        symbols with names matching regex.

common arguments:
  -i, --ignore-case     Enable case-insensitive searching.
  -v, --verbose         Enable verbose, full replication of the result column,
                        even if it means taking multiple lines per match (by
                        default the result will be condensed to keep one line
                        per match if possible).

dirs module:
  no additional arguments

files module:
  no additional arguments

symbols module:
  optional arguments:
    -u, --undefined     Also print undefined symbols (i.e. in objects which
                        reference but don't define the symbol).
```

## Examples
```sh
$ search search_modules 'def search\('
search_modules/files.py:65    def search(regex, paths, args, ignore_case=False, verbose=False):
search_modules/dirs.py:42     def search(regex, paths, args, ignore_case=False, verbose=False):
search_modules/symbols.py:485 def search(regex, paths, args, ignore_case=False, verbose=False):
```

```sh
$ search -i symbols -u test/symbols/*.o DIV
test/symbols/math_mul.o
Function symbol:
  Name:    _div
  Section: __TEXT,__text
  Value:   0x60
  Size:    0x0

test/symbols/util_number.o
Undefined symbol:
  Name:    _div
```

```sh
$ search dirs '.\.md'
./README.md
```

## Modules
`search` has been designed from the ground up to be extensible and has a module
system allowing the contribution of custom search modules to enable new ways to
search.

By itself the `search` utility does nothing - it is a CLI driver, loading and
initialising all available modules, parsing the command line and directing the
search request to the appropriate module.

`search` comes with three pre-written modules.
- `dirs`: Search recursively on the file names of any files in the given paths,
  similar to the Unix `find` command.
- `files`: Search recursively on the contents of any files in the given paths,
  similar to the Unix `grep` command. This is the default module which will be
  used if no module is specified.
- `symbols`: Search recursively in any object files or archives for symbols with
  names matching regex. This is similar to using `objdump` and `grep` in
  combination.


### Adding a module
If you have been provided with an additional module, you may install it by
placing it in the `search_modules` directory alongside the `search` executable.

### Writing a module
The driver will load all modules in the `search_modules` directory alongside the
`search` executable. With each of these it will bind the following methods:
- `create_subparser(subparsers)`
  This method will be called by the driver during module initialisation to allow
  the module to add a subparser to the main parser. This will then automatically
  contribute help text to the driver and allow selecting of the module in a
  query. Additional, module-specific arguments can be added to the subparser if
  necessary. **NB: Any added subparser must use the `add_help=False` keyword
  argument to prevent automatically adding help options.** Help options are added
  and handled by the driver.

  The arguments are as follows:
  - `subparsers`: Special handle object (`argparse._SubParsersAction`) which can
    be used to add subparsers to a parser.

  The return is as follows:
  - Object representing the created subparser.
- `search(regex, paths, args, ignore_case, verbose)`
  This method will be called to process a search query.

  The arguments are as follows:
  - `regex`: String regular expression to search with.
  - `paths`: List of strings representing the paths to search in/on.
  - `args`: Namespace containing all parsed arguments. If the subparser added
    additional arguments these will be present.
  - `ignore_case`: Boolean, True if the search should be case-insensitive,
    False if it should be case-sensitive.
  - `verbose`: Boolean, True for verbose output, False otherwise.

  The return is as follows:
  - Not expected to return anything. Any output must be printed by the method
    ifself.

The module loading will fail if these methods cannot be bound.

Putting all this together, if we wanted to add a new `dummy` module, the most
basic, functional implementation would look like the following:
```py
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
    for path in paths:
      # Do some kind of searching here...

def create_subparser(subparsers):
    """Creates this module's subparser.

    Args:
        subparsers: Special handle object (argparse._SubParsersAction) which can
            be used to add subparsers to a parser.

    Returns:
        Object representing the created subparser.
    """
    parser = subparsers.add_parser(
        'dummy',
        add_help=False,
        help='Do nothing at all.')
    return parser
```

Any `__version__` member in the module will be picked up as the module's
version information. All modules should have a 1.x version number: major
version numbers greater than this are reserved for future use.

There are a number of helper objects provided for describing search results,
formatting output and printing it to the console. These are briefly outlined
below and described in much more detail in the Python docstrings:
- `result`
  - Provides types necessary to build `SearchResult` objects.
  - `SearchResult`: container for describing a single result to a search query.
  - `Match`: abstract part of a `SearchResult` describing the component which
    matched the query. The `StringMatch` implementation is provided for a match
    found in a string (this will probably cover 90% of use cases). Modules may
    subclass if necessary to provide bespoke match types.
  - `Location`: abstract, optional part of a `SearchResult` describing where the
    match has been found. The `TextFileLocation` implementation is provided for
    a match which has been located in a text file. Modules may subclass if
    necessary to provide bespoke location types.
- `printer`
  - Provides printers for printing streamed `SearchResult` objects.
  - `AbstractPrinter`: abstract printer to print streamed `SearchResult`s. Once
    created the `print_results` method may be called on it with a `SearchResult`
    iterable to print the output. It is assumed the search query may be long
    running and it is desireable to print output as found (i.e. before
    termination), so it makes most sense to call this method with a generator
    function. A number of implementations of printers are provided. Modules may
    subclass if necessary to provide bespoke printers.
- `console`
  - Provides very basic console utility functions. Mostly used for writing
    custom printers.
- `ansi`
  - Provides utilities for adding ANSI formatting to a string (i.e. coloring it)
    for console output. Mostly used for writing custom match or location types.
- `process`
  - Provides wrappers to support streaming output from subprocesses. Mostly used
    for writing search modules which call out to separate tools or command line
    utilities.

Bringing all this together then, a skeleton, functional module might look like
the following:
```py
from search_utils.printer import MultiLinePrinter, SingleLinePrinter
from search_utils.process import StreamingProcess
from search_utils.result import SearchResult, StringMatch, TextFileLocation

# Module version.
__version__ = '1.0'

def parse_result(line, regex=None):
    """Creates a SearchResult object from the output of a grep command.

    Args:
        line:   String single line of grep output to process.
        regex:  String regex this result is derived from, or None if unknown.
            Defaults to None.

    Returns:
        The initialised SearchResult.
    """
    path_split = line.split(' ', 1)
    line_split = path_split[1].split(':', 1)
    return SearchResult(StringMatch(line_split[1].strip(), regex),
                        TextFileLocation(path_split[0], int(line_split[0])))

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
    with StreamingProcess(['grep', '-rnP', regex] + paths) as proc:
        printer = MultiLinePrinter() if verbose else SingleLinePrinter()
        printer.print_results(parse_result(line, regex) for line in proc)

def create_subparser(subparsers):
    """Creates this module's subparser.

    Args:
        subparsers: Special handle object (argparse._SubParsersAction) which can
            be used to add subparsers to a parser.

    Returns:
        Object representing the created subparser.
    """
    parser = subparsers.add_parser(
        'dummy',
        add_help=False,
        help='Do nothing very much.')
    return parser
```
This does roughly what the `files` module does, although simplified and
considerably less robust. Module authors are encouraged to review the provied
modules and the docstrings for further inspiration.
