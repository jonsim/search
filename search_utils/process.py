import subprocess

class StreamingProcess(object):
    def __init__(self, arglist):
        self.arglist = arglist
        self.proc = None
        self.returncode = None

    def __enter__(self):
        self.proc = subprocess.Popen(self.arglist, bufsize=4096,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     universal_newlines=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.returncode is None and self.proc.poll() is None:
            self.proc.terminate()

    def __iter__(self):
        return self

    def next(self):
        line = self.proc.stdout.readline()
        if line:
            return line[:-1]
        else:
            self.returncode = self.proc.returncode
            raise StopIteration