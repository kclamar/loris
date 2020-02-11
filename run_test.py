"""Run app for debugging
"""

from loris import conn, config

conn()

from loris.app.app import app

app.run(
    port=1234, debug=False,
    )
