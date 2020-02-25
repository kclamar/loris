"""Run app for debugging
"""

from loris import conn, config

conn()

from loris.app.app import app

app.run(
    port=1235, debug=True,
    host='0.0.0.0', 
    ssl_context='adhoc'
    )
