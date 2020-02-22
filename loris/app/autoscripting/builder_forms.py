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
    ParentInputRequired, Always, LookupNameValidator
)


class AutomaticFolderForm(Form, FormMixin):
    folder = DynamicFileField(
        'autoscript folder',
        description='upload your zipped autoscript folder',
        validators=[InputRequired(), Extension(['zip'])]
    )


def dynamic_scriptform(folderpath, form_names):
    class ScriptForm(NoCsrfForm, FormMixin):
        script_name = SelectField()
        required_forms = FieldList(SelectField())
        insert_db = BooleanField()
        configattr = StringField()
        outputfile = StringField()
        outputattr = StringField()


def dynamic_configfield(folderpath):
    class DynamicConfigField(NoCsrfForm, FormMixin):
        field_name = StringField()
        field_datatype = SelectField()
        folder_location = SelectField()
        folder_datatype = SelectField()
        selectfield_choices = FieldList(StringField())
        default = BooleanField()
        default_value = StringField()
        description = StringField()
        iterate = BooleanField()
