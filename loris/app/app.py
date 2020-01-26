"""
"""

from flask import Flask, session, request, redirect
from flask_dance.contrib.github import make_github_blueprint, github
from flask_login import LoginManager
from dash import Dash
import dash_html_components as html

from loris import config
from loris.app.login import User


class LorisApp(Flask):

    def session_refresh(self):
        config.refresh()
        # for testing when refresh happens
        session['schemata'] = list(config['schemata'].keys())
        session['tables'], session['autotables'] = config.tables_to_list()


app = LorisApp(__name__)
app.secret_key = config['secret_key']
blueprint = make_github_blueprint(
    client_id=config['client_id'],
    client_secret=config['client_secret'],
)
app.register_blueprint(blueprint, url_prefix="/login")

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
