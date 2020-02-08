"""subprocess class
"""

import subprocess

from flask import flash

from loris.errors import LorisError


class Run:

    def __init__(self):
        """
        """

        self._p = None

    @property
    def p(self):
        """
        """

        return self._p

    @p.setter
    def p(self, value):
        """
        """

        self._p = value

    @property
    def running(self):
        return self.p is not None and self.p.poll() is None

    def __call__(self, command):
        """
        """

        self.p = subprocess.Popen(
            command, shell=False,
            # stdout=subprocess.PIPE
        )

        return self.p

    def check(self):
        """check on subprocess and flash messages
        """
        if self.p is not None:
            if self.p.poll() is not None:
                if self.p.returncode == 0:
                    flash('Subprocess complete', 'success')
                    self.p = None
                else:
                    flash(f"Status of Subprocess: "
                          f"FAIL {self.p.returncode}", 'error')
                    self.p = None
            else:
                flash('Subprocess is still running', 'warning')
        else:
            flash('No subprocess is running', 'secondary')

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

        while self.p.poll() is None:
            pass

        return self.p.returncode
