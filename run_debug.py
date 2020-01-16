"""Run app for debugging
"""

import datajoint as dj

dj.config['database.host'] = '127.0.0.1'
dj.config['database.user'] = 'root'
dj.config['database.password'] = 'simple'
dj.conn()


from loris.app.app import app


app.run(debug=True)
