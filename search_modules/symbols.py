# Copyright (c) 2017 Jonathan Simmonds
"""Search module for searching for symbols within objects and archives."""
import argparse
import os.path
import re
import subprocess

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

    def __str__(self):
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
            self.abs_path = '%s::%s' % (archive_path, object_path)
        else:
            self.abs_path = object_path
        self.symbols = []

    def __str__(self):
        return 'OBJECT FILE %s:\n' % (self.abs_path) + \
               '\n'.join([str(s) for s in self.symbols])

    # __repr__ output is the same as as __str__
    __repr__ = __str__


def parse_symbol(line):
    """Parses a Symbol from an objdump symbol table entry.

    Args:
        line:   String line from an objdump symbol table entry.

    Returns:
        Symbol subclass parsed from the line, or None if it couldn't be parsed.
    """
    def _parse_elfsymbol(line):
        match = re.match(r'^(\S+)\s(.{7})\s(\S+)\s(\S+)\s(.+)$', line)
        if match:
            return ELFSymbol(*match.groups())
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
        match = re.match(r'^(.+):\s+file format', line)
        if match:
            current_file = ObjectFile(match.group(1), path)
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
    try:
        objdump = subprocess.check_output(['objdump', '-t', '-C', path],
                                          stderr=subprocess.PIPE).split('\n')
    except subprocess.CalledProcessError:
        return []
    # Strip and remove empty lines.
    objdump = [line.strip() for line in objdump]
    objdump = [line for line in objdump if line]
    # If no output left, bail.
    if not objdump:
        return []
    # Is this an archive?
    match = re.match(r'^.*[Aa]rchive\s+(.+):$', objdump[0])
    if match:
        return parse_archive(match.group(1), objdump[1:])
    # Otherwise maybe it's an object file?
    match = re.match(r'^(.+):\s+file format', objdump[0])
    if match:
        return [parse_object_file(match.group(1), objdump)]
    # Otherwise we've found something unexpected
    raise Exception('Unexpected objdump output for file ' + path)

def parse_directory(path, parse_all=True):
    """Parses a directory for ObjectFiles.

    Args:
        path:       String path to the directory.
        parse_all:  Boolean, True to parse all files in the directory for
            objects, False to parse only known file types.

    Returns:
        List of ObjectFile objects parsed from files in the given directory.
    """
    objects = []
    for dirname, subdirs, files in os.walk(path):
        for filename in files:
            if parse_all or any([filename.endswith(suffix) for suffix in
                                 ['.o', '.obj', '.a', '.so']]):
                objects += parse_file(os.path.join(dirname, filename))
    return objects

def main():
    """Main method."""
    # Handle command line
    parser = argparse.ArgumentParser(description='TODO')
    parser.add_argument('term', type=str,
                        help='The paths to read.')
    parser.add_argument('paths', type=str, default=None, nargs='+',
                        help='The paths to read.')
    args = parser.parse_args()

    objects = []
    for path in args.paths:
        if os.path.isdir(path):
            objects += parse_directory(path)
        elif os.path.isfile(path):
            objects += parse_file(path)
        else:
            raise Exception('Unrecognised path ' + path)
    for obj in objects:
        for sym in obj.symbols:
            if sym.name == args.term:
                print '%s:\n%s' % (obj.abs_path, sym)
    #if objects:
    #    print '\n\n'.join([str(o) for o in objects])


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
    print 'symbols search_result'

def create_subparser(subparsers):
    """Creates this module's subparser.

    Args:
        subparsers: Special handle object (argparse._SubParsersAction) which can
            be used to add subparsers to a parser.

    Returns:
        Object representing the created subparser.
    """
    parser = subparsers.add_parser('symbols', help='symbol mode', add_help=False)
    parser.add_argument('-d', action='store_const',
                        const=True, default=False,
                        help='Consider dynamic symbols')
    return parser

# Entry point.
if __name__ == '__main__':
    main()
