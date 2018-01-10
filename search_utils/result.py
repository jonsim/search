# Copyright (c) 2017-2018 Jonathan Simmonds
"""Module providing types necessary to build SearchResult objects."""
import os.path
import re
from search_utils import ansi

def lpad(string, width):
    """Inserts padding to the left of a string to be at least 'width' wide.

    Args:
        string: String to pad.
        width:  Width to make the string at least. May be 0 to not pad.

    Returns:
        Padded string.
    """
    if width > 0 and len(string) < width:
        return ' ' * (width - len(string)) + string
    return string

def rpad(string, width):
    """Inserts padding to the right of a string to be at least 'width' wide.

    Args:
        string: String to pad.
        width:  Width to make the string at least. May be 0 to not pad.

    Returns:
        Padded string.
    """
    if width > 0 and len(string) < width:
        return string + ' ' * (width - len(string))
    return string

def ltrunc(string, width, marker='...'):
    """Truncates a string from the left to be at most 'width' wide.

    Args:
        string: String to truncate.
        width:  Width to make the string at most. May be 0 to not truncate.
        marker: String to use in place of any truncated text.

    Returns:
        Truncated string.
    """
    if width > 0 and len(string) > width:
        return marker + string[-(width-len(marker)):]
    return string

def rtrunc(string, width, marker='...'):
    """Truncates a string from the right to be at most 'width' wide.

    Args:
        string: String to truncate.
        width:  Width to make the string at most. May be 0 to not truncate.
        marker: String to use in place of any truncated text.

    Returns:
        Truncated string.
    """
    if width > 0 and len(string) > width:
        return string[:-(width-len(marker))] + marker
    return string


# Result type

class SearchResult(object):
    """A single result to a search query.

    Attributes:
        match:      Match subclass describing the matched part of the result.
        location:   Location subclass describing the location of the result. May
            be None if the SearchResult does not have a location.
    """
    def __init__(self, match, location=None):
        """Initialises this SearchResult.

        Args:
            match:      Match subclass describing the matched part of the
                result.
            location:   Location subclass describing the location of the result.
                May be None if the SearchResult does not have a location.
        """
        if not isinstance(match, Match):
            raise TypeError('Invalid match type')
        if location is not None and not isinstance(location, Location):
            raise TypeError('Invalid location type')
        self.match = match
        self.location = location

    def __str__(self):
        if self.location:
            return '%s @ %s' % (str(self.match), str(self.location))
        return self.match

    __repr__ = __str__

    def format(self, decorate=True, match_col_width=0, loc_col_width=0,
               separator=' '):
        """Formats this result into a human presentable string.

        Args:
            decorate:           Boolean, True to apply ANSI decoration to the
                output string, False to just use pure text.
            match_col_width:    int maximum width of the match column, or 0 to
                not limit the match column's width.
            loc_col_width:      int maximum width of the location column, or 0
                to not limit the location column's width.
            separator:          String to use to separate the two columns. The
                width of this string is not taken into account in the width of
                either column.

        Returns:
            String human representation of the SearchResult.
        """
        match_str = self.match.format(decorate=decorate,
                                      min_width=0,
                                      max_width=match_col_width)
        if self.location:
            loc_str = self.location.format(decorate=decorate,
                                           min_width=loc_col_width,
                                           max_width=loc_col_width)
            return loc_str + separator + match_str
        else:
            return match_str


# Match types

class Match(object):
    """An abstract single match to a search query."""
    def __init__(self):
        """Initialises the Match."""
        pass

    def format(self, decorate=True, min_width=0, max_width=0):
        """Formats this match into a human presentable string.

        Args:
            decorate:   Boolean, True to apply ANSI decoration to the output
                string, False to just use pure text.
            min_width:  int minimum width to render the string presentation to.
                May be 0 to not limit the width of the rendered string.
            max_width:  int maximum width to render the string presentation to.
                May be 0 to not limit the width of the rendered string.

        Returns:
            String human representation of the Match.
        """
        raise NotImplementedError('Match must be subclassed')

    def length(self):
        """Calculates the visible length of the formatted string representing
        this Match if its width were not limited.

        Returns:
            int width of the unrestricted Match format string.
        """
        raise NotImplementedError('Match must be subclassed')

class StringMatch(Match):
    """A match to a search query in a text string.

    Attributes:
        match:          String full line of text which contains the match.
        regex:          String regex which matched the line. May be None if
            unknown.
        ignore_case:    Boolean, True if case was ignored when matching the
            regex, False if case was not ignored.
    """
    # The character sequence to place at the truncation point in result lines
    _RES_CONT = '...'

    def __init__(self, match, regex=None, ignore_case=False):
        """Initialises the Match.

        Args:
            match:          String full line of the text file which contains the
                match.
            regex:          String regex which matched the line. May be None if
                unknown.
            ignore_case:    Boolean, True if case was ignored when matching the
                regex, False if case was not ignored.
        """
        super(StringMatch, self).__init__()
        self.match = match
        self.regex = regex
        self.ignore_case = ignore_case

    def __str__(self):
        if self.regex:
            return 'match="%s", regex="%s"' % (self.match, self.regex) + \
                   ' (-i)' if self.ignore_case else ''
        return 'match="%s"' % (self.match)

    __repr__ = __str__

    def format(self, decorate=True, min_width=0, max_width=0):
        if self.regex:
            re_flags = re.IGNORECASE if self.ignore_case else 0
        formatted = self.match

        # If too long, truncate.
        if max_width > 0 and len(formatted) > max_width:
            # If we've been given the search truncate intelligently, trying to
            # retain at least one match. Otherwise just truncate from the right
            re_r = re.search(self.regex, formatted, flags=re_flags) if self.regex else None
            start_pos = re_r.start(0) - 10 if re_r and re_r.start(0) > 10 else 0
            end_pos = start_pos + max_width
            if end_pos > len(formatted):
                start_pos -= end_pos - len(formatted)
                end_pos = len(formatted)
            start_trunc = start_pos > 0
            end_trunc = end_pos < len(formatted)
            if start_trunc:
                start_pos += len(self._RES_CONT)
            if end_trunc:
                end_pos -= len(self._RES_CONT)
            formatted = formatted[start_pos:end_pos]
            if start_trunc:
                formatted = self._RES_CONT + formatted
            if end_trunc:
                formatted = formatted + self._RES_CONT

        # If decorating and we know the regex, highlight the search term.
        if decorate and self.regex:
            re_split = re.split('(%s)' % (self.regex), formatted, flags=re_flags)
            for i in range(1, len(re_split), 2):
                re_split[i] = ansi.decorate(re_split[i], ansi.BOLD, ansi.FG_RED)
            formatted = ''.join(re_split)

        # If too short, left pad.
        lpad(formatted, min_width)

        # Return whatever we have left.
        return formatted

    def length(self):
        return len(self.match)


# Location types

class Location(object):
    """An abstract location of a single match to a search query."""
    def __init__(self):
        """Initialises the Location."""
        pass

    def format(self, decorate=True, min_width=0, max_width=0):
        """Formats this location into a human presentable string.

        Args:
            decorate:   Boolean, True to apply ANSI decoration to the output
                string, False to just use pure text.
            min_width:  int minimum width to render the string presentation to.
                May be 0 to not limit the width of the rendered string.
            max_width:  int maximum width to render the string presentation to.
                May be 0 to not limit the width of the rendered string.

        Returns:
            String human representation of the Location.
        """
        raise NotImplementedError('Location must be subclassed')

    def length(self):
        """Calculates the visible length of the formatted string representing
        this Location if its width were not limited.

        Returns:
            int width of the unrestricted Match format string.
        """
        raise NotImplementedError('Location must be subclassed')

class TextFileLocation(Location):
    """The location of a match to a search query in a text file.

    Attributes:
        path:       String path of the file in which the match occurs.
        basename:   String name of the file.
        dirname:    String path to the directory (including trailing separator).
        line:       int 1-indexed line number of the match in the file.
    """

    def __init__(self, path, line=-1):
        """Initialises the Location.

        Args:
            path:   String path of the file in which the match occurs.
            line:   int line number on which the match occurs. May be -1 if the
                line number is not known or relevant.
        """
        super(TextFileLocation, self).__init__()
        self.path = path
        self.basename = os.path.basename(path)
        self.dirname = os.path.dirname(path) + os.path.sep
        self.line = line

    def __str__(self):
        if self.line < 0:
            return self.path
        return '%s:%d' % (self.path, self.line)

    __repr__ = __str__

    def format(self, decorate=True, min_width=0, max_width=0):
        def _format_path(max_width=0):
            """Internal method to extract and format the path."""
            formatted = ltrunc(self.path, max_width)
            if decorate:
                # If there is some of the dirname visible, split the string and
                # format it.
                basename_len = len(self.basename)
                if len(formatted) > basename_len:
                    dirname_part = ansi.decorate(formatted[:-basename_len], ansi.FG_YELLOW)
                    basename_part = ansi.decorate(formatted[-basename_len:], ansi.BOLD, ansi.FG_YELLOW)
                    formatted = dirname_part + basename_part
                else:
                    formatted = ansi.decorate(formatted, ansi.BOLD, ansi.FG_YELLOW)
            return formatted

        def _format_line():
            """Internal method to extract and format the line number."""
            if self.line < 0:
                return ''
            formatted = ':' + str(self.line)
            # Decorate if necessary.
            if decorate:
                formatted = ansi.decorate(formatted, ansi.FG_YELLOW)
            return formatted

        if max_width > 0:
            formatted = _format_line()
            # While we can afford to add more to the string, keep adding.
            curlen = ansi.length(formatted)
            if curlen < max_width:
                formatted = _format_path(max_width=max_width-curlen) + formatted
        else:
            formatted = _format_path() + _format_line()

        if min_width > 0:
            # If too short, right pad.
            curlen = ansi.length(formatted)
            if curlen < min_width:
                formatted = formatted + ' ' * (min_width - curlen)

        return formatted

    def length(self):
        return len('%s:%d' % (self.path, self.line))
