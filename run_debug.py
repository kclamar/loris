"""Run app for debugging
"""

from loris import conn, config

conn()

from loris.app.app import app

app.run(debug=True)
