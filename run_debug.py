"""Run app for debugging
"""

import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "true"

from loris import conn, config

conn()

from loris.app.app import app

app.run(debug=True)
