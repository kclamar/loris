"""subprocess class
"""

import subprocess
import threading

from flask import flash

from loris.errors import LorisError


class Run:
    """run a thread
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.p = None
        self.cmd = None
        self.cwd = None
        self.lines = []
        self.rc = None
        self.stderr = ''
        self.thread = None

    @property
    def running(self):
        return self.p is not None and self.p.poll() is None

    def start(self, cmd, cwd):
        self.reset()
        self.cmd = cmd
        self.cwd = cwd
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):

        self.p = subprocess.Popen(
            self.cmd, shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.cwd, bufsize=1
        )

        while True:
            output = self.p.stdout.readline()
            if self.p.poll() is not None:
                break
            if output:
                self.lines.append(output)
        self.rc = self.p.poll()
        _, self.stderr = self.p.communicate()

    @property
    def stdout(self):
        return ''.join(self.lines)

    def check(self):
        """check on subprocess and flash messages
        """

        if self.rc is not None:
            if self.rc == 0:
                flash('Subprocess complete', 'success')
            else:
                flash(f"Subprocess failed: "
                      f"{self.rc}", 'error')
            self.p = None
        elif self.p is not None:
            flash('Subprocess is still running', 'warning')
        else:
            flash('No subprocess is running', 'secondary')

        return self.stdout.splitlines(), self.stderr.splitlines()

    def abort(self):
        """abort subprocess
        """
        if self.p is not None:
            self.p.terminate()
            self.p = None
            flash('Aborting subprocess...', 'warning')
        else:
            flash('No subprocess is running')

    def wait(self):
        """wait for the subprocess to finish
        """

        if self.p is None:
            raise LorisError('No subprocess is running.')

        self.thread.join()

        return self.rc, self.stdout, self.stderr
