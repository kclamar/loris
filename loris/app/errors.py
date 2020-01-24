"""handling of errors
"""

import traceback
from flask import flash, render_template
from loris.app.app import app


class LoginError(Exception):

    def __init__(self, error_id=0):

        if error_id == 0:
            super().__init__('Click on Loris.')
        elif error_id == 1:
            super().__init__(
                'GitHub account does not match'
                ' with any existing experimenters.'
            )
        elif error_id == 1:
            super().__init__(
                'GitHub authorization bad.'
            )
        else:
            super().__init__('')


@app.errorhandler(LoginError)
def login_error(e):
    return render_template('pages/login_error.html', message=str(e)), 500


@app.errorhandler(Exception)
def error(e):
    error_traceback = traceback.format_exc().splitlines()
    flash(error_traceback[-1], 'error')
    return render_template('pages/error.html', traceback=error_traceback), 500
