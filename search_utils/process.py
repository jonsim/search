# (c) Copyright 2017 Jonathan Simmonds
"""Module providing wrappers to support streaming output from subprocesses."""
import subprocess

class StreamingProcess(object):
    """Context manager providing support for streaming output from a subprocess.

    As an iterable context manager, this is intended to be used in a 'with'
    block and iterated as follows:

    ...
    with StreamingProcess(['ls', '-l']) as proc:
        for line in proc:
            print line
        print proc.returncode
    ...

    Attributes:
        arglist:    List of string arguments to invoke the subprocess with.
        proc:       Popen object representing the underlying subprocess.
        returncode: int return code of the subprocess, set to None if the
            process has not yet exitted.
    """
    def __init__(self, arglist):
        """Creates the context manager. The subprocess is not spawned until
        entered.

        Args:
            arglist:    List of string arguments to invoke the subprocess with.
        """
        self.arglist = arglist
        self.proc = None
        self.returncode = None

    def __str__(self):
        return 'StreamingProcess(%s)' % (str(self.arglist))

    __repr__ = __str__

    def __enter__(self):
        """Called when the context manager is entered. Spawns the subprocess.

        Returns:
            An iterable object over the process's stdout and stderr streams
            (they are piped together). Retrieved by the 'as' keyword in a 'with'
            block.
        """
        self.proc = subprocess.Popen(self.arglist, bufsize=4096,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     universal_newlines=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Called when the context manager is exitted. Terminates the subprocess
        if it has not already exitted.

        Args:
            exc_type:   Type of the exception that caused this exit. None if no
                exception caused the exit.
            exc_value:  Exception object that caused this exit. None if no
                exception caused the exit.
            traceback:  Traceback of the exception that caused this exit. None
                if no exception caused the exit.
        """
        if self.returncode is None and self.proc.poll() is None:
            self.proc.terminate()

    def __iter__(self):
        """Called on an iterable to retrieve an iterator.

        Returns:
            An iterator.
        """
        return self

    def __next__(self):
        """Python3 next()."""
        return self.next()

    def next(self):
        """Called on an iterator to retrieve the next element, or raise
        StopIteration if there is no next object.

        Raises:
            StopIteration:  If there are no more objects left. In this case the
                returncode attribute will have been set and may be used to
                retrieve the process's exit status.

        Returns:
            The next line from the process's stdout and stderr stream (they are
            combined together). The returned line will not have a trailing
            newline.
        """
        line = self.proc.stdout.readline()
        # Readline always returns a line suffixed by '\n', unless it reads EOF
        # in which case it will return ''. We strip off the trailing '\n'.
        if line:
            return line[:-1]
        else:
            self.returncode = self.proc.returncode
            raise StopIteration
