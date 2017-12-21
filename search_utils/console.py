# Copyright (c) 2017 Jonathan Simmonds
"""Module providing very basic console utility functions."""
import fcntl
import termios
import struct

_CONSOLE_CACHE = None

def size(use_cache=True):
    """Derives the current console's size.

    NB: Taken from http://stackoverflow.com/a/3010495

    Returns:
        (width, height) of the current console.
    """
    global _CONSOLE_CACHE
    if not use_cache or not _CONSOLE_CACHE:
        try:
            h, w, hp, wp = struct.unpack('HHHH', fcntl.ioctl(1,
                termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
        except IOError:
            w, h = (80, 40)
        _CONSOLE_CACHE = (w, h)
    return _CONSOLE_CACHE
