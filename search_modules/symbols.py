# Copyright (c) 2017 Jonathan Simmonds
"""Search module for searching for symbols within objects and archives."""
import os.path
import re
import sys
from search_utils import ansi
from search_utils.process import StreamingProcess
from search_utils.result import SearchResult, Match, Location, ltrunc, rpad
from search_utils.printer import MultiLinePrinter

# Module version.
__version__ = '1.0'

# List of the known file suffixes to search for object files. May be empty to
# search all files. Files which are searched which are not of the correct type
# will be silently ignored, so leaving this empty is most likely to succeed, but
# may be slower in the presence of lots of non-object files, which will all be
# parsed to work out if they are actually object files.
KNOWN_TYPES = []
# KNOWN_TYPES = ['.o', '.obj', '.a', '.so']

class Symbol(object):
    """An abstract representation of a single Symbol object.

    Attributes:
        value:      int value of the symbol. In different symbol formats this is
            alternately known as the offset or address of the symbol.
        section:    String name of the section this symbol resides in.
        size:       int size of the symbol, typically in bytes.
        name:       String name of the symbol.
        is_local:   Boolean, True if this symbol has local scope.
        is_global:  Boolean, True if this symbol has global scope.
        is_unique:  Boolean, True if this symbol is a 'unique' global - i.e. it
            has greater scope than even global symbols. This state is only
            represented by a few formats.
        is_weak:    Boolean, True if the symbol has weak binding - i.e. it can
            be overridden by a strong symbol (the default binding).
        is_ctor:    Boolean, True if the symbol represents a constructor.
        is_warning: Boolean, True if the symbol should generate warnings if
            referenced.
        is_ref:     Boolean, True if the symbol is an indirect reference to
            another symbol.
        is_reloc:   Boolean, True if the symbol is a function to be evaluated
            during reloc processing.
        is_debug:   Boolean, True if the symbol is a debugging symbol.
        is_dynamic: Boolean, True if the symbol is a dynamic symbol.
        is_func:    Boolean, True if the symbol represents a function.
        is_file:    Boolean, True if the symbol represents a file.
        is_object:  Boolean, True if the symbol represents an object.
        is_defined: Boolean, True if the symbol is defined, False if the symbol
            is just a reference in lieu of a defined version of the symbol.
    """
    def __init__(self, value, section, size, name):
        """Initialises the Symbol.

        Args:
            value:      int value of the symbol. In different symbol formats
                this is alternately known as the offset or address of the
                symbol.
            section:    String name of the section this symbol resides in.
            size:       int size of the symbol, typically in bytes.
            name:       String name of the symbol.
        """
        self.value = value
        self.section = section
        self.size = size
        self.name = name
        # Zero flags (Symbol itself is considered abstract whereas the flags
        # are very much implementation details).
        self.is_local = False
        self.is_global = False
        self.is_unique = False
        self.is_weak = False
        self.is_ctor = False
        self.is_warning = False
        self.is_ref = False
        self.is_reloc = False
        self.is_debug = False
        self.is_dynamic = False
        self.is_func = False
        self.is_file = False
        self.is_object = False
        self.is_defined = False

    def format_flags(self):
        """Retrieves a textual representation of each of the symbol's flags.

        Returns:
            List of strings representing each of the symbol's flags. May be
            empty if this symbol has no flags.
        """
        flags = []
        if self.is_unique:
            flags.append('Unique')
        if self.is_weak:
            flags.append('Weak')
        if self.is_ctor:
            flags.append('Constructor')
        if self.is_warning:
            flags.append('Warning')
        if self.is_ref:
            flags.append('Indirect reference')
        if self.is_reloc:
            flags.append('Reloc function')
        if self.is_debug:
            flags.append('Debug')
        if self.is_dynamic:
            flags.append('Dynamic')
        if self.is_func:
            flags.append('Function')
        if self.is_file:
            flags.append('File')
        if self.is_object:
            flags.append('Object')
        return flags

    def __str__(self):
        flags = self.format_flags()
        if flags:
            flag_str = '    Flags:\n      ' + '\n      '.join(flags)
        else:
            flag_str = ''
        if self.is_defined:
            return  '  %s\n' \
                    '    Section = %s\n' \
                    '    Value: 0x%X\n' \
                    '    Size:  0x%X\n%s' % (self.name, self.section,
                                             self.value, self.size, flag_str)
        else:
            return  '  %s\n' \
                    '    UNDEFINED\n%s' % (self.name, flag_str)

    # __repr__ output is the same as as __str__
    __repr__ = __str__


class ELFSymbol(Symbol):
    """A Symbol object representing an ELF formatted symbol."""
    def __init__(self, value, flags, section, size, name):
        Symbol.__init__(self, int(value, 16), section, int(size, 16), name)
        # Parse flags.
        self.is_local   = flags[0] in ['l', '!']
        self.is_global  = flags[0] in ['g', 'u', '!']
        self.is_unique  = flags[0] == 'u'
        self.is_weak    = flags[1] == 'w'
        self.is_ctor    = flags[2] == 'C'
        self.is_warning = flags[3] == 'W'
        self.is_ref     = flags[4] == 'i'
        self.is_reloc   = flags[4] == 'I'
        self.is_debug   = flags[5] == 'd'
        self.is_dynamic = flags[5] == 'D'
        self.is_func    = flags[6] == 'F'
        self.is_file    = flags[6] == 'f'
        self.is_object  = flags[6] == 'O'
        self.is_defined = section != '*UND*'


class ObjectFile(object):
    """An object file, existing either directly on disk or in an archive.

    Attributes:
        object_path:    String path to the object file. If this object is
            outside of an archive, this must be an absolute path to the object
            file, or if this object is in an archive, this must be a relative
            path to the archive_path.
        archive_path:   String path to the archive this object file is in, or
            None if the object file is not in an archive.
        abs_path:       String absolute path to the object file (regardless of
            its location).
        symbols:        List of Symbols contained in this object file.
    """
    def __init__(self, object_path, archive_path):
        """Initialises the ObjectFile.

        Args:
        object_path:    String path to the object file. If this object is
            outside of an archive, this must be an absolute path to the object
            file, or if this object is in an archive, this must be a relative
            path to the archive_path.
        archive_path:   String path to the archive this object file is in, or
            None if the object file is not in an archive.
        """
        if archive_path and not os.path.isfile(archive_path):
            raise Exception('No such archive file ' + archive_path)
        elif not archive_path and not os.path.isfile(object_path):
            raise Exception('No such object file ' + object_path)
        self.object_path = object_path
        self.archive_path = archive_path
        if archive_path:
            self.abs_path = '%s(%s)' % (archive_path, object_path)
        else:
            self.abs_path = object_path
        self.symbols = []

    def __str__(self):
        return 'OBJECT FILE %s:\n' % (self.abs_path) + \
               '\n'.join([str(s) for s in self.symbols])

    # __repr__ output is the same as as __str__
    __repr__ = __str__


class SymbolMatch(Match):
    """A match to a search query in a symbol.

    Attributes:
        symbol:         The symbol whose name matched the search query.
        regex:          String regex which matched the symbol. May be None if
            unknown.
        ignore_case:    Boolean, True if case was ignored when matching the
            regex, False if case was not ignored.
    """
    def __init__(self, symbol, regex=None, ignore_case=None):
        """Initialises the Match.

        Args:
            symbol:         The symbol whose name matched the search query.
            regex:          String regex which matched the symbol. May be None
                if unknown.
            ignore_case:    Boolean, True if case was ignored when matching the
                regex, False if case was not ignored.
        """
        super(SymbolMatch, self).__init__()
        self.symbol = symbol
        self.regex = regex
        self.ignore_case = ignore_case

    def format(self, decorate=True, min_width=0, max_width=0):
        flags = self.symbol.format_flags()
        # Build type string from the flags.
        if not self.symbol.is_defined:
            flags.insert(0, 'Undefined')
        if flags:
            type_str = '%s symbol:' % (', '.join(flags))
        else:
            type_str = 'symbol:'
        # Fix casing.
        type_str = type_str.capitalize()

        # Build and decorate the name string.
        # If decorating and we know the regex, highlight the search term.
        if decorate and self.regex:
            re_flags = re.IGNORECASE if self.ignore_case else 0
            re_split = re.split('(%s)' % (self.regex), self.symbol.name,
                                flags=re_flags)
            for i in range(1, len(re_split), 2):
                re_split[i] = ansi.decorate(re_split[i], ansi.BOLD, ansi.FG_RED)
            name_str = '  Name:    %s' % (''.join(re_split))
        else:
            name_str = '  Name:    %s' % (self.symbol.name)

        # Add symbol description if necessary.
        lines = [type_str, name_str]
        if self.symbol.is_defined:
            lines.append('  Section: %s' % (self.symbol.section))
            lines.append('  Value:   0x%x' % (self.symbol.value))
            lines.append('  Size:    0x%x' % (self.symbol.size))
        return '\n'.join(lines)

    def length(self):
        raise NotImplementedError('SymbolMatch does not support length limits')


class ObjectFileLocation(Location):
    """The location of a match to a search query in an object file.

    Attributes:
        object_file:    ObjectFile object representing the parsed object file in
            which the match was found.
    """
    def __init__(self, object_file):
        """Initialises the Location.

        Args:
            object_file:    ObjectFile object representing the parsed object
                file in which the match was found.
        """
        super(ObjectFileLocation, self).__init__()
        self.object_file = object_file

    def __str__(self):
        return self.object_file.abs_path

    __repr__ = __str__

    def format(self, decorate=True, min_width=0, max_width=0):
        if self.object_file.archive_path:
            formatted = ltrunc(self.object_file.abs_path, max_width)
            # Archive path formatting
            abs_len = len(self.object_file.abs_path)
            path_len = len(self.object_file.archive_path)
            dir_len = len(os.path.dirname(self.object_file.archive_path) + os.path.sep)
            obj_len = len(self.object_file.object_path)
            # Split with right-references to take into account that we may have
            # just truncated the parts we're trying to split out.
            split = [formatted[:-(abs_len - dir_len)],
                     formatted[-(abs_len - dir_len):-(abs_len - path_len)],
                     formatted[-(obj_len + 2):-(obj_len + 1)],
                     formatted[-(obj_len + 1):-1],
                     formatted[-1:]]
            if split[0]:    # Archive dirname
                split[0] = ansi.decorate(split[0], ansi.FG_YELLOW)
            if split[1]:    # Archive basename
                split[1] = ansi.decorate(split[1], ansi.FG_YELLOW)
            if split[2]:    # (
                split[2] = ansi.decorate(split[2], ansi.FG_YELLOW)
            if split[3]:    # Object basename
                split[3] = ansi.decorate(split[3], ansi.FG_YELLOW, ansi.BOLD)
            if split[4]:    # )
                split[4] = ansi.decorate(split[4], ansi.FG_YELLOW)
            formatted = ''.join(split)
            return rpad(formatted, min_width)
        else:
            formatted = ltrunc(self.object_file.abs_path, max_width)
            # Object path formatting
            base_len = len(os.path.basename(self.object_file.abs_path))
            split = [formatted[:-base_len], formatted[-base_len:]]
            if split[0]:    # Object dirname
                split[0] = ansi.decorate(split[0], ansi.FG_YELLOW)
            if split[1]:    # Object basename
                split[1] = ansi.decorate(split[1], ansi.FG_YELLOW, ansi.BOLD)
            formatted = ''.join(split)
            return rpad(formatted, min_width)

    def length(self):
        return len(self.object_file.abs_path)

def parse_symbol(line):
    """Parses a Symbol from an objdump symbol table entry.

    Args:
        line:   String line from an objdump symbol table entry.

    Returns:
        Symbol subclass parsed from the line, or None if it couldn't be parsed.
    """
    def _parse_elfsymbol(line):
        # First try the standard ELF symbol table encoding.
        match = re.match(r'^(\S+)\s(.{7})\s(\S+)\s(\S+)\s(.+)$', line)
        if match:
            return ELFSymbol(*match.groups())
        # Failing that, try the bastardised Mach-O symbol table encoding.
        match = re.match(r'^(\S+)\s(.{7})\s(\S+)\s(.+)$', line)
        if match:
            return ELFSymbol(match.group(1), match.group(2), match.group(3), '0', match.group(4))
        return None

    def _parse_othersymbol(line):
        """
                [  4](sec  3)(fl 0x00)(ty   0)(scl   3) (nx 1) 0x00000000 .bss
                [  6](sec  1)(fl 0x00)(ty   0)(scl   2) (nx 0) 0x00000000 fred

        where the number inside the square brackets is the number of the entry in
        the symbol table, the sec number is the section number, the fl value are the
        symbol's flag bits, the ty number is the symbol's type, the scl number is
        the symbol's storage class and the nx value is the number of auxilary
        entries associated with the symbol. The last two fields are the symbol's
        value and its name.
        """
        return None

    if not line:
        return None
    # Return first successful parsing.
    sym = _parse_elfsymbol(line)
    if sym is not None:
        return sym
    return _parse_othersymbol(line)

def parse_object_file(path, objdump):
    """Parses an ObjectFile from an objdump output.

    Args:
        path:       String path to the object file.
        objdump:    List of strings of lines of objdump output to parse.

    Returns:
        ObjectFile object representing the parsed object file.
    """
    objfile = ObjectFile(path, None)
    for line in objdump:
        sym = parse_symbol(line)
        if not sym:
            if objfile.symbols:
                break
            continue
        objfile.symbols.append(sym)
    return objfile

def parse_archive(path, objdump):
    """Parses a list of ObjectFiles from an objdump archive output.

    Args:
        path:       String path to the archive.
        objdump:    List of strings of lines of objdump output to parse.

    Returns:
        List of ObjectFile objects representing the objects contained within the
        archive.
    """
    object_files = []
    current_file = None
    for line in objdump:
        match = re.match(r'^(.+)\((.+)\):\s+file format', line)
        if match:
            filename = match.group(2) if match.group(2) else match.group(1)
            current_file = ObjectFile(filename, path)
            object_files.append(current_file)
            continue
        if not current_file:
            raise Exception('Archive does not specify object to attribute '
                            'symbols to ' + path)
        sym = parse_symbol(line)
        if not sym:
            if current_file.symbols:
                current_file = None
            continue
        current_file.symbols.append(sym)
    return object_files

def parse_file(path):
    """Parses a file for ObjectFiles.

    Args:
        path:   String path to the file.

    Returns:
        List of ObjectFile objects parsed from the given file.
    """
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # Assume Linux has GNU objdump. This has the options:
        # -t (list symbols), -C (de-mangle symbol names)
        objdump_args = ['objdump', '-t', '-C']
    elif sys.platform.startswith('darwin'):
        # Assume OSX has LLVM objdump. This has the options:
        # -t (list symbols)
        objdump_args = ['objdump', '-t']
    objdump_args.append(path)
    with StreamingProcess(objdump_args) as proc:
        # Find the first non-blank line.
        first_line = proc.peek()
        while not first_line:
            proc.next()
            first_line = proc.peek()
        # Is this an archive?
        match = re.match(r'^.*[Aa]rchive\s+(.+):$', first_line)
        if match:
            return parse_archive(match.group(1), proc)
        # Some objdumps format archives differently.
        match = re.match(r'^(.+)\((.+)\):\s+file format', first_line)
        if match:
            return parse_archive(match.group(1), proc)
        # Otherwise maybe it's an object file?
        match = re.match(r'^(.+):\s+file format', first_line)
        if match:
            return [parse_object_file(match.group(1), proc)]
        # Otherwise it's not an archive or object file.
        return []

def search_file(path, regex, ignore_case, include_undefined, printer):
    """Perform the requested search on a file.

    Args:
        path:               String path to a file to search.
        regex:              String regular expression to search with.
        ignore_case:        Boolean, True if the search should be
            case-insensitive, False if it should be case-sensitive.
        include_undefined:  Boolean, True if the search should include symbols
            which are undefined.
        printer:            AbstractPrinter subclass to use to print the results
            to the search.
    """
    re_flags = re.IGNORECASE if ignore_case else 0
    object_files = parse_file(path)
    results = []
    for object_file in object_files:
        for symbol in object_file.symbols:
            if not include_undefined and not symbol.is_defined:
                continue
            if re.search(regex, symbol.name, flags=re_flags):
                results.append(SearchResult(SymbolMatch(symbol, regex, ignore_case),
                                            ObjectFileLocation(object_file)))
    printer.print_results(results)

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
    printer = MultiLinePrinter()
    for path in paths:
        if os.path.isdir(path):
            for dirname, subdirs, files in os.walk(path):
                for filename in files:
                    if not KNOWN_TYPES or any([filename.endswith(suffix) for
                                               suffix in KNOWN_TYPES]):
                        search_file(os.path.join(dirname, filename), regex,
                                    ignore_case, args.undefined, printer)
        else:
            search_file(path, regex, ignore_case, args.undefined, printer)

def create_subparser(subparsers):
    """Creates this module's subparser.

    Args:
        subparsers: Special handle object (argparse._SubParsersAction) which can
            be used to add subparsers to a parser.

    Returns:
        Object representing the created subparser.
    """
    parser = subparsers.add_parser(
        'symbols',
        add_help=False,
        help='Search recursively in any object files or archives for symbols '
             'with names matching regex.')
    parser.add_argument(
        '-u', '--undefined',
        dest='undefined', action='store_const', const=True, default=False,
        help='Also print undefined symbols (i.e. in objects which reference '
             'but don\'t define the symbol).')
    return parser
