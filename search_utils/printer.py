# Copyright (c) 2017 Jonathan Simmonds
"""Module providing printers for printing streamed SearchResults."""
from search_utils import console

class AbstractPrinter(object):
    """An abstract printer for printing streamed SearchResults."""
    def __init__(self):
        pass

    def print_results(self, result_iterable):
        """Prints SearchResults to stdout.

        Args:
            result_iterable:    An iterable object which will yield SearchResult
                objects for this printer to print. Any None objects are ignored.
                Unless the printer otherwise states, the objects are printed as
                they are iterated (i.e. they are not buffered). To take
                advantage of this, this argument is best given as a generator
                to permit printing of output before termination of the source.
        """
        raise NotImplementedError('AbstractPrinter must be subclassed')

class BufferingTwoColumnPrinter(AbstractPrinter):
    """A printer which reads all the results from an iterator into an internal
    buffer before printing them in two columns (location and match). All the
    results must be read before printing can begin in order for the columns to
    be correctly sized.
    """
    def __init__(self, condense_location=True, condense_match=True,
                 max_minimisation=16):
        """Creates a new printer.

        Args:
            condense_location:  Boolean, True to permit minimising the location
                column if the result cannot otherwise be printed on a single
                line; False to always print the full location column.
            condense_match:     Boolean, True to permit minimising the match
                column if the result cannot otherwise be pritned on a single
                line; False to always print the full match column.
            max_minimisation:   int minimum number of characters a minimisation
                may reduce a string to.
        """
        super(BufferingTwoColumnPrinter, self).__init__()
        self.condense_location = condense_location
        self.condense_match = condense_match
        self.max_minimisation = max_minimisation
        self.col_spacing = 1
        self.decorate = True

    def print_results(self, result_iterable):
        console_width, console_height = console.size()
        results = []
        max_loc_col = 0
        max_match_col = 0
        # Scoop out all results and the max string information.
        for result in result_iterable:
            if not result:
                continue
            results.append(result)
            max_loc_col = max(result.location.length(), max_loc_col)
            max_match_col = max(result.match.length(), max_match_col)
        # Work out what we can do with them.
        min_loc_col = min(self.max_minimisation, max_loc_col) \
                        if self.condense_location else max_loc_col
        min_match_col = min(self.max_minimisation, max_match_col) \
                          if self.condense_match else max_match_col

        # If the longest line can fit on the screen, print normally.
        if max_loc_col + self.col_spacing + max_match_col <= console_width:
            for result in results:
                print result.format(decorate=self.decorate,
                                    match_col_width=max_match_col,
                                    loc_col_width=max_loc_col)
        # If we can't print normally, could we print if we minimised just the
        # location column (prefer condensing location to match)?
        elif min_loc_col + self.col_spacing + max_match_col <= console_width:
            # If that will fit, print the maximum we can get away with.
            for result in results:
                print result.format(decorate=self.decorate,
                                    match_col_width=max_match_col,
                                    loc_col_width=console_width - max_match_col - self.col_spacing)
        # If we still can't fit anything in, could we print if we minimised just
        # the match column?
        elif max_loc_col + self.col_spacing + min_match_col <= console_width:
            # If that will fit, print the maximum we can get away with.
            for result in results:
                print result.format(decorate=self.decorate,
                                    match_col_width=console_width - max_loc_col - self.col_spacing,
                                    loc_col_width=max_loc_col)
        # If that still isn't working, what about if we minimised both sides?
        elif min_loc_col + self.col_spacing + min_match_col <= console_width:
            # If that will fit, print the columns in a 1:2 ratio.
            for result in results:
                print result.format(decorate=self.decorate,
                                    match_col_width=(console_width / 3) * 2,
                                    loc_col_width=console_width / 3)
        # If all else fails, just print the results on separate lines
        else:
            for result in results:
                print result.format(decorate=self.decorate,
                                    separator='\n') + '\n'


class SingleLinePrinter(AbstractPrinter):
    """A printer which attempts to print the results from an iterator each to a
    single line.
    """
    def __init__(self, condense_location=True, condense_match=True,
                 max_minimisation=16):
        """Creates a new printer.

        Args:
            condense_location:  Boolean, True to permit minimising the location
                column if the result cannot otherwise be printed on a single
                line; False to always print the full location column.
            condense_match:     Boolean, True to permit minimising the match
                column if the result cannot otherwise be pritned on a single
                line; False to always print the full match column.
            max_minimisation:   int minimum number of characters a minimisation
                may reduce a string to.
        """
        super(SingleLinePrinter, self).__init__()
        self.condense_location = condense_location
        self.condense_match = condense_match
        self.max_minimisation = max_minimisation
        self.col_spacing = 1
        self.decorate = True

    def print_results(self, result_iterable):
        console_width, console_height = console.size()
        for result in result_iterable:
            if not result:
                continue
            loc_len = result.location.length()
            match_len = result.match.length()
            # Can we just print the line?
            if loc_len + self.col_spacing + match_len <= console_width:
                print result.format(decorate=self.decorate)
            # If not, can we print it if we squish the location column?
            elif (self.condense_location and self.max_minimisation +
                  self.col_spacing + match_len <= console_width):
                print result.format(decorate=self.decorate,
                                    loc_col_width=console_width - match_len - self.col_spacing)
            # If not, can we print it if we squish the match column?
            elif (self.condense_match and loc_len + self.col_spacing +
                  self.max_minimisation <= console_width):
                print result.format(decorate=self.decorate,
                                    match_col_width=console_width - loc_len - self.col_spacing)
            # If not, can we print it if we squish both columns?
            elif (self.condense_location and self.condense_match and
                  self.max_minimisation * 2 + self.col_spacing <= console_width):
                print result.format(decorate=self.decorate,
                                    match_col_width=(console_width / 3) * 2,
                                    loc_col_width=console_width / 3) - self.col_spacing
            # If all else fails, just print the whole lot together.
            else:
                print result.format(decorate=self.decorate)

class MultiLinePrinter(AbstractPrinter):
    """A printer which prints each result from an iterator fully across multiple
    lines. The result is never truncated.
    """
    def __init__(self):
        """Creates a new printer."""
        super(MultiLinePrinter, self).__init__()
        self.decorate = True

    def print_results(self, result_iterable):
        for result in result_iterable:
            if not result:
                continue
            if result.location:
                print result.format(decorate=self.decorate, separator='\n') + '\n'
            else:
                print result.format(decorate=self.decorate)
