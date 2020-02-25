"""class for building analysis
"""

import datetime
import os
import warnings
import pandas as pd
import numpy as np
import pickle
import json
import uuid
import glob

import datajoint as dj
from datajoint.declare import match_type
from datajoint import FreeTable
from datajoint.table import lookup_class_name
from datajoint.utils import to_camel_case
from flask import url_for
from wtforms import BooleanField, SelectField, DateField, DateTimeField, \
    StringField, FloatField, IntegerField, FormField, \
    TextAreaField, FieldList, DecimalField, HiddenField
from wtforms.validators import InputRequired, Optional, NumberRange, \
    ValidationError, Length, UUID, URL, Email
from werkzeug.datastructures import FileStorage
from wtforms import FieldList, FormField, BooleanField, StringField, \
    TextAreaField, SelectField
from wtforms.widgets import HiddenInput
from flask_wtf import FlaskForm as Form
from wtforms import Form as NoCsrfForm
from flask_wtf.file import FileField
from werkzeug.utils import secure_filename

from loris import config
from loris.utils import is_manuallookup
from loris.app.utils import name_lookup, datareader
from loris.app.forms import NONES
from loris.app.forms.formmixin import (
    FormMixin,
    ManualLookupForm, ParentFormField, DynamicFileField, DictField, ListField,
    ParentValidator, JsonSerializableValidator, AttachFileField,
    BlobFileField, Extension, TagListField, MetaHiddenField,
    ParentInputRequired, Always, LookupNameValidator, DictTextArea
)


class AutomaticFolderForm(Form, FormMixin):
    folder = DynamicFileField(
        'autoscript folder',
        description='upload your zipped autoscript folder',
        validators=[InputRequired(), Extension(['zip'])]
    )


def dynamic_scriptform(folderpath):
    class ScriptForm(NoCsrfForm, FormMixin):
        button = StringField(
            'button',
            description='button name to display',
            validators=[InputRequired()]
        )
        script = SelectField(
            'script',
            description='script to run when clicking the button',
            validators=[InputRequired()],
            choices=[
                filename
                for filename in glob.glob(os.path.join(folderpath, '*'))
                if filename.endswith('.py')
            ]
        )
        validate = TagListField(
            'validate',
            description='names of forms to validate upon pressing button',
            validators=[Optional()]
        )
        insert = BooleanField(
            'insert',
            description=(
                'whether to insert into database '
                'after running the script'
            ),
            validators=[Optional()]
        )
        configattr = StringField(
            'configattr',
            description=(
                'column name in experiment form '
                'to save the configuration file'
            ),
            validators=[Optional()]
        )
        outputfile = StringField(
            'outputfile',
            description=(
                'name of the output file from the autoscript'
            ),
            validators=[Optional()]
        )
        outputattr = StringField(
            'outputattr',
            description=(
                'column name in experiment form '
                'to save the output file'
            ),
            validators=[Optional()]
        )

    return ScriptForm


class FormConfig(NoCsrfForm, FormMixin):
    name = StringField(
        'name',
        description=(
            'name of the additional form'
        ),
        validators=[InputRequired()]
    )
    form_config = DictTextArea(
        'form configuration',
        description=(
            'dictionary configuration of additional form'
        ),
        validators=[InputRequired(), JsonSerializableValidator(dict)]
    )


def dynamic_formbuilder(folderpath):

    class FormBuilder(Form, FormMixin):
        buttons = FieldList(
            FormField(dynamic_scriptform(folderpath))
        )
        forms = FieldList(
            FormField(FormConfig)
        )
