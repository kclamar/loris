"""handling of errors
"""

import traceback
from flask import flash, render_template
from loris.app.app import app


@app.errorhandler(Exception)
def error(e):
    error_traceback = traceback.format_exc().splitlines()
    flash(error_traceback[-1], 'error')
    return render_template('pages/error.html', traceback=error_traceback), 500
