"""
"""

from flask import Flask
from loris import config

app = Flask(__name__)
app.secret_key = config['secret_key']

from loris.app import views
