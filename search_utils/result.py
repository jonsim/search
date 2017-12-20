import os.path
import re
from search_utils import ansi

def _lpad(string, width):
    if width > 0 and len(string) < width:
        return ' ' * (width - len(string)) + string
    return string

def _rpad(string, width):
    if width > 0 and len(string) < width:
        return string + ' ' * (width - len(string))
    return string

def _ltrunc(string, width, marker='...'):
    if width > 0 and len(string) > width:
        return marker + string[-(width-len(marker)):]
    return string

def _rtrunc(string, width, marker='...'):
    if width > 0 and len(string) > width:
        return string[:-(width-len(marker))] + marker
    return string


# Result type

class SearchResult(object):
    def __init__(self, match, location=None):
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

    def format(self, decorate=True, match_col_width=0, loc_col_width=0,
               separator=' '):
        match_str = self.match.format(decorate=decorate,
                                      min_width=0,
                                      max_width=match_col_width)
        if self.location:
            loc_str = self.location.format(decorate=True,
                                           min_width=loc_col_width,
                                           max_width=loc_col_width)
            return loc_str + separator + match_str
        else:
            return match_str


# Match types

class Match(object):
    def __init__(self):
        pass

    def format(self, decorate=True, max_width=0):
        raise NotImplementedError('Match must be subclassed')

    def length(self):
        raise NotImplementedError('Match must be subclassed')

class TextFileMatch(Match):
    # The character sequence to place at the truncation point in result lines
    _RES_CONT = '...'

    def __init__(self, match, regex=None, ignore_case=False):
        self.match = match
        self.regex = regex
        self.ignore_case = ignore_case

    def __str__(self):
        if self.regex:
            return 'match="%s", regex="%s"%s' % (self.match, self.regex,
                                                     ' (-i)' if self.ignore_case else '')
        return 'match="%s"' % (self.match)

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
        _lpad(formatted, min_width)

        # Return whatever we have left.
        return formatted

    def length(self):
        return len(self.match)


# Location types

class Location(object):
    def __init__(self):
        pass

    def format(self, decorate=True, max_width=0):
        raise NotImplementedError('Location must be subclassed')

    def length(self):
        raise NotImplementedError('Location must be subclassed')

class TextFileLocation(Location):

    def __init__(self, path, line=-1):
        self.path = path
        self.basename = os.path.basename(path)
        self.dirname = os.path.dirname(path) + os.path.sep
        self.line = line

    def __str__(self):
        if self.line < 0:
            return self.path
        return '%s:%d' % (self.path, self.line)

    def format(self, decorate=True, min_width=0, max_width=0):
        def _format_path(max_width=0):
            formatted = _ltrunc(self.path, max_width)
            if decorate:
                # If there is some of the dirname visible, split the string and
                # format it.
                basename_len = len(self.basename)
                if len(formatted) > basename_len:
                    dirname_part = ansi.decorate(formatted[:-basename_len], ansi.FG_YELLOW)
                    basename_part = ansi.decorate(formatted[-basename_len:], ansi.FG_YELLOW, ansi.BOLD)
                    formatted = dirname_part + basename_part
                else:
                    formatted = ansi.decorate(formatted, ansi.FG_YELLOW, ansi.BOLD)
            return formatted

        def _format_dirname(max_width=0):
            """Internal method to extract and format/truncate/pad the dirname."""
            # Truncate as necessary.
            formatted = _ltrunc(self.dirname, max_width)
            # Decorating if necessary.
            if decorate:
                formatted = ansi.decorate(formatted, ansi.FG_YELLOW)
            return formatted

        def _format_basename(max_width=0):
            """Internal method to extract and format/truncate/pad the basename."""
            # Truncate as necessary.
            formatted = _ltrunc(self.basename, max_width)
            # Decorate if necessary.
            if decorate:
                formatted = ansi.decorate(formatted, ansi.BOLD, ansi.FG_YELLOW)
            return formatted

        def _format_line():
            """Internal method to extract and format/truncate/pad the lineno."""
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
            #     formatted = _format_basename(max_width=max_width-curlen) + formatted
            # curlen = ansi.length(formatted)
            # if curlen < max_width:
            #     formatted = _format_dirname(max_width=max_width-curlen) + formatted
        else:
            formatted = _format_dirname() + _format_basename() + _format_line()

        if min_width > 0:
            # If too short, right pad.
            curlen = ansi.length(formatted)
            if curlen < min_width:
                formatted = formatted + ' ' * (min_width - curlen)

        return formatted

    def length(self):
        return len('%s:%d' % (self.path, self.line))
