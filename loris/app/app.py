"""
"""

from flask import Flask, session
from flask_dance.contrib.gitlab import make_gitlab_blueprint

from loris import config


class LorisApp(Flask):

    def session_refresh(self):
        config.refresh()
        # for testing when refresh happens
        print('refreshed!')
        session['schemata'] = list(config['schemata'].keys())
        session['tables'] = config.tables_to_list()


app = LorisApp(__name__)
app.secret_key = config['secret_key']
blueprint = make_gitlab_blueprint(
    client_id=config['client_id'],
    client_secret=config['client_secret'],
)
app.register_blueprint(blueprint, url_prefix="/login")


from loris.app import views, errors
