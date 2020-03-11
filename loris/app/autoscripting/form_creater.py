"""Class to dynamically create the different forms in the config file
"""

import os
from wtforms import (
    BooleanField, SelectField, StringField, FloatField, IntegerField,
    FormField, TextAreaField, FieldList, DecimalField
)
from wtforms.validators import InputRequired, Optional, NumberRange, \
    ValidationError, Length, UUID, URL, Email
from flask_wtf import FlaskForm as Form
from wtforms import Form as NoCsrfForm
from werkzeug.utils import secure_filename
import glob

from loris import config
from loris.app.forms import NONES
from loris.app.forms.formmixin import (
    DynamicFileField, DictField, ListField,
    JsonSerializableValidator, Extension, FormMixin
)
from loris.app.autoscripting.utils import (
    json_reader, array_reader, recarray_reader,
    frame_reader, series_reader, EnumReader, ListReader, TupleReader,
    DictReader
)
from loris.errors import LorisError


class AutoscriptedField:

    def __init__(self, key, value, folderpath):
        self.key = key
        self.folderpath = folderpath

        if isinstance(value, (str, list)):
            self.value = value
            self.description = None
            self.default = None
            self.required = True
            self.iterate = None
            self.loc = None
        elif isinstance(value, dict):
            truth = set(value) - {'type', 'comment', 'default', 'loc', 'iterate'}
            if truth:
                raise LorisError(
                    'Key in dynamic auto-generated form contains '
                    f'illegal keywords: {truth}.'
                )
            if 'type' not in value:
                raise LorisError(
                    'Must provide type key for dynamic auto-generated form; '
                    f'only provided these keys for "{key}": {set(value)}.'
                )
            self.value = value.get('type')
            self.description = value.get('comment', None)
            self.default = value.get('default', None)
            self.required = (
                'default' not in value
                or value.get('default', None) is not None)
            self.loc = value.get('loc', None)
            self.iterate = value.get('iterate', False)
        else:
            LorisError(f"value is wrong type {type(value)}")

        self.get_field()

    def get_field(self):
        """get initialized field
        """

        self.field, self.post_process = self._get_field(
            self.key, self.value, self.required, self.default,
            self.description, self.iterate, self.loc, self.folderpath
        )

    @staticmethod
    def file_processing(value):

        if value == 'numpy.array':
            post_process = array_reader
        elif value == 'numpy.recarray':
            post_process = recarray_reader
        elif value == 'pandas.DataFrame':
            post_process = frame_reader
        elif value == 'pandas.Series':
            post_process = series_reader
        elif value == 'json':
            post_process = json_reader
        else:
            return lambda x: x

        return post_process

    @classmethod
    def _get_field(
        cls, key, value, required, default, description,
        iterate, loc, folderpath
    ):
        """get initialized field
        """

        def post_process(x):
            return x

        if required:
            kwargs = {
                'validators': [InputRequired()],
                'render_kw': {'nullable': False}
            }
        else:
            kwargs = {
                'validators': [Optional()],
                'render_kw': {'nullable': True}
            }

        kwargs['default'] = default
        kwargs['label'] = key.replace('_', ' ')
        kwargs['description'] = (key if description is None else description)

        if loc is None and not isinstance(value, dict):
            if value == 'list':
                kwargs['validators'].append(JsonSerializableValidator())
                field = ListField(**kwargs)
            elif value == 'dict':
                kwargs['validators'].append(JsonSerializableValidator())
                field = DictField(**kwargs)
            elif value == 'str':
                field = StringField(**kwargs)
            elif value == 'set':
                kwargs['validators'].append(JsonSerializableValidator())
                post_process = set
                field = ListField(**kwargs)
            elif value == 'tuple':
                kwargs['validators'].append(JsonSerializableValidator())
                post_process = tuple
                field = ListField(**kwargs)
            elif value == 'int':
                field = IntegerField(**kwargs)
            elif value == 'float':
                field = FloatField(**kwargs)
            elif value == 'bool':
                kwargs['validators'] = [Optional()]
                field = BooleanField(**kwargs)
            elif value == 'numpy.array':
                kwargs['validators'].append(Extension())
                post_process = cls.file_processing(value)
                field = DynamicFileField(**kwargs)
            elif value == 'numpy.recarray':
                kwargs['validators'].append(Extension())
                post_process = cls.file_processing(value)
                field = DynamicFileField(**kwargs)
            elif value == 'pandas.DataFrame':
                kwargs['validators'].append(Extension())
                post_process = cls.file_processing(value)
                field = DynamicFileField(**kwargs)
            elif value == 'pandas.Series':
                kwargs['validators'].append(Extension())
                post_process = cls.file_processing(value)
                field = DynamicFileField(**kwargs)
            elif value == 'json':
                kwargs['validators'].append(Extension(['json']))
                post_process = cls.file_processing(value)
                field = DynamicFileField(**kwargs)
            elif value == 'file':
                kwargs['validators'].append(
                    Extension(config['attach_extensions']))
                field = DynamicFileField(**kwargs)
            elif isinstance(value, list):
                choices = [
                    str(ele).strip().strip('"').strip("'")
                    for ele in value
                ]
                post_process = EnumReader(value, choices)

                if default is None:
                    choices = ['NULL'] + choices
                kwargs['choices'] = [(ele, ele) for ele in choices]

                field = SelectField(**kwargs)
            else:
                raise LorisError(
                    f"field value {value} not accepted for {key}."
                )
        elif loc is not None and isinstance(value, str):
            loc = secure_filename(loc)
            locpath = os.path.join(folderpath, loc)
            # try up to two base directories down
            if not os.path.exists(locpath):
                # try main autoscript folder
                locpath = os.path.join(os.path.dirname(folderpath), loc)
                if not os.path.exists(locpath):
                    locpath = os.path.join(
                        os.path.dirname(os.path.dirname(folderpath)), loc
                    )
                    if not os.path.exists(locpath):
                        raise LorisError(
                            f'Folder "{loc}" does not exist in '
                            f'autoscript folder '
                            f'"{os.path.basename(folderpath)}" '
                            f'and also not in the main autoscript folder.'
                        )
            # get all files from folder
            files = glob.glob(os.path.join(locpath, '*'))
            # only match certain extensions
            if (value == 'pandas.DataFrame') or (value == 'numpy.recarray'):
                files = [
                    ifile for ifile in files
                    if (
                        ifile.endswith('.pkl')
                        or ifile.endswith('.npy')
                        or ifile.endswith('.csv')
                        or ifile.endswith('.json')
                    )
                ]
            elif value == 'numpy.array':
                files = [
                    ifile for ifile in files
                    if (
                        ifile.endswith('.pkl')
                        or ifile.endswith('.npy')
                        or ifile.endswith('.csv')
                    )
                ]
            elif (value == 'json') or (value == 'pandas.Series'):
                files = [ifile for ifile in files if ifile.endswith('.json')]
            else:
                # skip file that start with two underscores e.g. __init__.py
                files = [
                    ifile
                    for ifile in files
                    if not os.path.basename(ifile).startswith('__')
                ]
            # setup as choices
            choices = [
                (str(ele), os.path.split(ele)[-1])
                for ele in files
            ]
            # setup None choice
            if default is None and not required:
                choices = [('NULL', 'NULL')] + choices
            kwargs['choices'] = choices
            post_process = cls.file_processing(value)
            field = SelectField(**kwargs)
        elif isinstance(value, dict):
            form, post_process = dynamic_autoscripted_form(
                value, folderpath, NoCsrfForm
            )
            field = FormField(form)
        # TODO set number of fieldlists (startswith numeric)
        else:
            raise LorisError(f"field value {value} not accepted for {key}.")

        # make iterator (can add multiple values together)
        if iterate:
            field = FieldList(
                field,
                min_entries=int(required) + 1  # have one required field if so
            )
            post_process = ListReader(post_process)
        return field, post_process


def dynamic_autoscripted_form(dictionary, folderpath, formclass=Form):

    post_process_dict = {}

    class DynamicForm(formclass, FormMixin):
        pass

    for key, value in dictionary.items():
        # comments in the json or formatting guidelines start with _
        if key.startswith('#'):
            continue
        if not key.isidentifier():
            raise LorisError(
                f"key {key} is not an identifier; i.e. alphanumeric "
                "and underscore characters only. The key needs to be "
                "an identifier if it is used as a keyword during function "
                "calling."
            )

        auto_field = AutoscriptedField(
            key, value, folderpath
        )

        post_process_dict[key] = auto_field.post_process

        setattr(
            DynamicForm,
            key,
            auto_field.field
        )

    return DynamicForm, DictReader(post_process_dict)
