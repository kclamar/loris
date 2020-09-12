"""
"""

from flask import Flask, session, request, redirect
from flask_login import LoginManager
from dash import Dash
import dash_html_components as html

from loris import config
from loris.app.login import User


if config['init_database']:
    from loris.database.schema import (
        anatomy, experimenters,
        imaging, subjects, core
    )


class LorisApp(Flask):

    def session_refresh(self):
        config.refresh()
        # for testing when refresh happens
        config.refresh()
        self.config['schemata'] = list(config['schemata'].keys())
        self.config['tables'], self.config['autotables'] = \
            config.tables_to_list()


app = LorisApp(__name__)
app.secret_key = config['secret_key']
app.config['include_fish'] = config['include_fish']
app.config['external_wiki'] = config['external_wiki']
app.config['schemata'] = list(config['schemata'].keys())
app.config['tables'], app.config['autotables'] = config.tables_to_list()

login_manager = LoginManager(app)

# Test of dash app
dash_app = Dash(__name__, server=app, url_base_pathname='/dashapp/')
dash_app.layout = html.Div(
    children=[html.H1(children='Dash App')]
)


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login?target=' + request.path)


from loris.app import views, errors
