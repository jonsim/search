#!/usr/bin/env python
# (c) Copyright 2017 Jonathan Simmonds
import argparse
import os.path
import re
import subprocess

class Symbol(object):
    def __init__(self, value, section, size, name):
        self.value = value
        self.section = section
        self.size = size
        self.name = name
        # Zero flags (Symbol itself is considered abstract whereas the flags
        # are very much implementation details)
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
        flag_str = ''
        if self.is_unique:  flag_str += '      Unique\n'
        if self.is_weak:    flag_str += '      Weak\n'
        if self.is_ctor:    flag_str += '      Constructor\n'
        if self.is_warning: flag_str += '      Warning\n'
        if self.is_ref:     flag_str += '      Indirect reference\n'
        if self.is_reloc:   flag_str += '      Reloc function\n'
        if self.is_debug:   flag_str += '      Debug\n'
        if self.is_dynamic: flag_str += '      Dynamic\n'
        if self.is_func:    flag_str += '      Function\n'
        if self.is_file:    flag_str += '      File\n'
        if self.is_object:  flag_str += '      Object\n'
        if flag_str:
            flag_str = '    Flags:\n' + flag_str
        if self.is_defined:
            return  '  %s\n' \
                    '    Section = %s\n' \
                    '    Value: 0x%X\n' \
                    '    Size:  0x%X\n%s' % (self.name, self.section, self.value,
                                         self.size, flag_str)
        else:
            return  '  %s\n' \
                    '    UNDEFINED\n%s' % (self.name, flag_str)

    # __repr__ output is the same as as __str__
    __repr__ = __str__


class ELFSymbol(Symbol):
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
    def __init__(self, object_path, archive_path):
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
        return 'OBJECT FILE %s:\n%s' % (self.abs_path, '\n'.join([str(s) for s in self.symbols]))

    # __repr__ output is the same as as __str__
    __repr__ = __str__


def parse_ELFSymbol(line):
    match = re.match(r'^(\S+)\s(.{7})\s(\S+)\s(\S+)\s(.+)$', line)
    if match:
        return ELFSymbol(*match.groups())
    return None

def parse_OtherSymbol(line):
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

def parse_Symbol(line):
    if not line:
        return None
    # Return first successful parsing.
    sym = parse_ELFSymbol(line)
    if sym is not None:
        return sym
    return parse_OtherSymbol(line)

def parse_ObjectFile(path, objdump):
    objfile = ObjectFile(path, None)
    for line in objdump:
        sym = parse_Symbol(line)
        if not sym:
            if objfile.symbols:
                break
            continue
        objfile.symbols.append(sym)
    return objfile

def parse_Archive(path, objdump):
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
        sym = parse_Symbol(line)
        if not sym:
            if current_file.symbols:
                current_file = None
            continue
        current_file.symbols.append(sym)
    return object_files

def parse_file(path):
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
        return parse_Archive(match.group(1), objdump[1:])
    # Otherwise maybe it's an object file?
    match = re.match(r'^(.+):\s+file format', objdump[0])
    if match:
        return [parse_ObjectFile(match.group(1), objdump)]
    # Otherwise we've found something unexpected
    raise Exception('Unexpected objdump output for file ' + path)

def parse_directory(path, parse_all=True):
    KNOWN_TYPES = ['.o', '.obj', '.a', '.so']
    objects = []
    for dirname, subdirs, files in os.walk(path):
        for filename in files:
            if parse_all or any([filename.endswith(suffix) for suffix in KNOWN_TYPES]):
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
    print 'symbols search_result'

def get_subparser(subparsers):
    parser = subparsers.add_parser('symbols', help='symbol mode', add_help=False)
    parser.add_argument('-d', action='store_const',
                        const=True, default=False,
                        help='Consider dynamic symbols')
    return parser

# Entry point.
if __name__ == '__main__':
    main()
