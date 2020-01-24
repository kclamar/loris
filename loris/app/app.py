"""
"""

from flask import Flask, session
from flask_dance.contrib.github import make_github_blueprint, github

from dash import Dash
import dash_html_components as html

from loris import config


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

# Test of dash app
dash_app = Dash(__name__, server=app, url_base_pathname='/dashapp/')
dash_app.layout = html.Div(
    children=[html.H1(children='Dash App')]
)


from loris.app import views, errors
