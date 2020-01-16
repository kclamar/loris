"""
"""

from flask import Flask

app = Flask(__name__)
app.secret_key = 'myprecious'

from . import views
