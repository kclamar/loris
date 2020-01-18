"""fixed forms
"""

import pandas as pd
import numpy as np
import os
import graphviz
from flask_wtf import FlaskForm as Form
from flask import render_template, request, flash, url_for, redirect
import datajoint as dj
from datajoint.table import lookup_class_name
from wtforms import Form as NoCsrfForm
from wtforms import StringField, IntegerField, BooleanField, FloatField, \
    SelectField, FieldList, FormField, HiddenField
from wtforms.validators import InputRequired, Optional

from loris import config
from loris.app.forms.formmixin import FormMixin


def dynamic_jointablesform():

    class JoinTablesForm(Form, FormMixin):
        tables_dict = config['tables']
        tables = FieldList(
            SelectField(
                'tables',
                choices=[(key, key) for key in tables_dict],
                validators=[InputRequired()]
            ),
            min_entries=1
        )
        restriction = StringField(
            'restrictions',
            description='a sql restriction to apply to the joined table',
            validators=[Optional()]
        )

    return JoinTablesForm
