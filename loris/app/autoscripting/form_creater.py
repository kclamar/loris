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


class AutoscriptedField:

    def __init__(self, key, value, description=None):
        self.key = key
        self.description = (
            key if description is None else description
        )

        if isinstance(value, list):
            self.value = value[0]
            self.default = value[1]
            self.required = self.default is not None
        else:
            self.required = True
            self.value = value
            self.default = None

        self.get_field()

    def get_field(self):
        """get initialized field
        """

        self.field, self.post_process = self._get_field(
            self.key, self.value, self.default,
            self.required, self.description
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
    def _get_field(cls, key, value, default, required, description):
        """get initialized field
        """

        def post_process(x):
            return x

        if required:
            kwargs = {
                'validators': [InputRequired()]
            }
        else:
            kwargs = {
                'validators': [Optional()]
            }

        kwargs['default'] = default
        kwargs['label'] = key
        kwargs['description'] = description

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
            kwargs['validators'].append(Extension(config['attach_extensions']))
            field = DynamicFileField(**kwargs)
        elif isinstance(value, str) and value.startswith('folder'):
            _, folder_name, value = value.split('---')
            files = glob.glob(os.path.join(folder_name, '*'))
            choices = [
                (str(ele), os.path.split(ele)[-1])
                for ele in files
            ]

            if default is None:
                choices = [('NULL', 'NULL')] + choices
            kwargs['choices'] = choices
            post_process = cls.file_processing(value)
            field = SelectField(**kwargs)
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
        elif isinstance(value, str) and value.startswith('list'):
            value = value.split('---')[-1]

            field, post_process = cls._get_field(
                key, value, default, required, description
            )

            field = FieldList(
                field,
                min_entries=1
            )
            post_process = ListReader(post_process)
        elif isinstance(value, str) and value.startswith('tuple'):
            value = value.split('---')[-1]

            field, post_process = cls._get_field(
                key, value, default, required, description
            )

            field = FieldList(
                field,
                min_entries=1
            )
            post_process = TupleReader(post_process)
        elif isinstance(value, dict):
            form, post_process = dynamic_autoscripted_form(
                value, NoCsrfForm
            )

            if value.get('_iterate', False):
                field = FieldList(
                    FormField(form),
                    min_entries=1
                )
                post_process = ListReader(post_process)
            else:
                field = FormField(form)
        # TODO set number of fieldlists (startswith numeric)
        else:
            raise NameError(f"field value {value} not accepted.")

        return field, post_process


def dynamic_autoscripted_form(dictionary, formclass=Form):

    post_process_dict = {}

    class DynamicForm(formclass, FormMixin):
        pass

    for key, value in dictionary.items():
        # comments in the json or formatting guidelines start with _
        if key.startswith('_'):
            continue

        auto_field = AutoscriptedField(
            key, value, dictionary.get('_descriptions', {}).get(key, None)
        )

        post_process_dict[key] = auto_field.post_process

        setattr(
            DynamicForm,
            key,
            auto_field.field
        )

    return DynamicForm, DictReader(post_process_dict)
