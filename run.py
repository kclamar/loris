"""Run app for debugging
"""

from loris import conn, config

conn()

from loris.app.app import app

from flask import Flask


'''app.run(
    port=1234, debug=False,
    host='0.0.0.0'
    )
'''
if __name__ == "__main__":
    from waitress import serve
    serve(app, port=1234,host='0.0.0.0')
