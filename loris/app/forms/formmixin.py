"""Wtf Forms
"""

import os
import numpy as np
import json
import re

from wtforms import FieldList, FormField, BooleanField, StringField, \
    TextAreaField, SelectField
from wtforms.widgets import HiddenInput
from wtforms import Form as NoCsrfForm
from flask_wtf.file import FileField
from werkzeug.utils import secure_filename
from wtforms.validators import InputRequired, Optional, NumberRange, \
    ValidationError, Length, UUID, URL, Email, StopValidation
import datajoint as dj

from loris import config
from loris.app.forms import NONES


class MetaHiddenField(BooleanField):
    widget = HiddenInput()


class TagListField(StringField):
    """Stringfield for a list of separated tags"""

    def __init__(
        self, label='', validators=None, remove_duplicates=True,
        to_lowercase=True, separator=' ', **kwargs
    ):
        """
        Construct a new field.
        :param label: The label of the field.
        :param validators: A sequence of validators to call when validate is called.
        :param remove_duplicates: Remove duplicates in a case insensitive manner.
        :param to_lowercase: Cast all values to lowercase.
        :param separator: The separator that splits the individual tags.
        """
        super(TagListField, self).__init__(label, validators, **kwargs)
        self.remove_duplicates = remove_duplicates
        self.to_lowercase = to_lowercase
        self.separator = separator
        self.data = []

    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(self.separator)]
            if self.remove_duplicates:
                self.data = list(self._remove_duplicates(self.data))
            if self.to_lowercase:
                self.data = [x.lower() for x in self.data]

    @classmethod
    def _remove_duplicates(cls, seq):
        """
        Remove duplicates in a case insensitive,
        but case preserving manner
        """
        d = {}
        for item in seq:
            if item.lower() not in d:
                d[item.lower()] = True
                yield item


class EvalJsonField(StringField):

    startswith = None
    endswith = None

    def process_data(self, value):
        return super().process_data(str(value))

    @property
    def noneval_data(self):
        data = super().__getattribute__('data')
        if data in NONES:
            return ''
        else:
            if (
                data.startswith(self.startswith)
                and data.endswith(self.endswith)
            ):
                return data
            else:
                return f'{self.startswith}{data}{self.endswith}'

    @property
    def eval_data(self):
        data = self.noneval_data
        if data in NONES:
            return data
        else:
            return json.loads(data)

    def __getattribute__(self, name):
        # dirty trick to get evaluated data
        if name == 'data':
            return self.eval_data
        else:
            return super().__getattribute__(name)


class ListField(EvalJsonField):

    startswith = '['
    endswith = ']'


class DictField(EvalJsonField):

    startswith = '{'
    endswith = '}'


class RestrictionField(StringField):

    def process_data(self, value):
        return super().process_data(str(value))

    def evaluate(self, data):
        if data.startswith('['):
            return True
        elif data.startswith('{'):
            return True
        else:
            return False

    @property
    def noneval_data(self):
        data = super().__getattribute__('data')
        return data

    @property
    def eval_data(self):
        data = self.noneval_data
        if data in NONES:
            return ''
        elif self.evaluate(data):
            return json.loads(data)
        else:
            return data

    def __getattribute__(self, name):
        # dirty trick to get evaluated data
        if name == 'data':
            return self.eval_data
        else:
            return super().__getattribute__(name)


class DynamicFileField(FileField):
    pass  # TODO


class CamelCaseValidator:

    def __init__(self, name='table name'):

        self.name = name

    def __call__(self, form, field):

        if not re.match(r'[A-Z][a-zA-Z0-9]*', field.data):
            raise ValidationError(
                f'{self.name} must be alphanumeric in CamelCase, '
                'begin with a capital letter.'
            )


class Extension:
    """Extension Validator
    """

    def __init__(self, ext=config['extensions']):
        self.ext = ext

    def __call__(self, form, field):
        filename = field.data.filename
        if not filename:
            return
        extension = os.path.splitext(filename)[-1].strip('.')
        if extension not in self.ext:
            raise ValidationError(
                f"File {filename} is not of extension: {self.ext}, "
                f"but extension {extension}."
            )


class FilePath:

    def __call__(self, form, field):

        data = field.data
        if not os.path.exists(data):
            raise ValidationError(
                f'Filepath {data} does not exist.'
            )


class ParentInputRequired(Optional):

    def __call__(self, form, field):
        """only required if <new> set
        """

        try:
            existing = getattr(form, 'existing_entries').data
        except AttributeError:
            existing = '<new>'

        if existing == '<new>':
            if field.data in NONES:
                raise ValidationError('Data missing!')

        super().__call__(form, field)


class Always:

    def __call__(self, form, field):
        try:
            existing = getattr(form, 'existing_entries').data
        except AttributeError:
            existing = '<new>'

        if existing == '<new>':
            raise ValidationError("Data completely missing!")


class ParentValidator:

    def __init__(self, primary_key):
        self.primary_key = primary_key

    def __call__(self, form, field):
        """
        """

        data = getattr(form, self.primary_key).data

        if field.data == '<new>':
            if data in NONES:
                raise ValidationError(
                    'Must specify new foreign primary key '
                    'if <add new entry> is selected.'
                )
            if str(data) in [ele for ele, ele in field.choices]:
                raise ValidationError(
                    f'Entry {data} already exists in parent table.'
                )

        else:
            if data not in NONES:
                raise ValidationError(
                    'If specifying new foreign primary key '
                    'need to set select field to <add new entry>'
                )


class JsonSerializableValidator:

    def __call__(self, form, field):

        if hasattr(field, 'noneval_data'):
            data = field.noneval_data
        else:
            data = field.data

        try:
            json.loads(data)
        except Exception as e:
            raise ValidationError(
                f'Data is not a json-serializable: {e}'
            )


class OptionalJsonSerializableValidator(JsonSerializableValidator):

    def __call__(self, form, field):

        if field.evaluate(field.noneval_data):
            super().__call__(form, field)


class BlobFileField(DynamicFileField):
    pass


class AttachFileField(DynamicFileField):
    pass


class FormMixin:
    hidden_entries = None

    def populate_form(self, formatted_dict):
        """populate form from formatted_dict

        Parameters
        ----------
        formatted_dict : dict
            dictionary as formatted by get_formatted method.
        readonly : iterable
            field ids that are readonly.
        """
        for field in self:
            key = field.short_name

            if key in formatted_dict:
                data = formatted_dict[key]

                if data is None:
                    continue

                elif isinstance(field, FieldList):
                    while len(field) > 1:
                        field.pop_entry()

                    subfield = field[0]

                    if isinstance(subfield, FormField):
                        for idata in data:
                            sanitized_data = subfield.populate_form(idata).data
                            field.append_entry(sanitized_data)

                    else:
                        for idata in data:
                            field.append_entry(idata)

                elif isinstance(field, FormField):
                    field.populate_form(data)

                else:
                    field.process_data(data)

        return self

    def rm_hidden_entries(self):
        """removes hidden entries in form to allow for dynamic lists
        """

        self.hidden_entries = {}
        self.subhidden_entries = []

        for field in self:

            if isinstance(field, FormField):
                field.rm_hidden_entries()
                self.subhidden_entries.append(field)

            elif isinstance(field, FieldList):

                hidden_entry = field.entries.pop(0)
                self.hidden_entries[field] = hidden_entry

                for subfield in field:
                    # check if subfield is formfield and pop entry
                    if isinstance(subfield, FormField):
                        subfield.rm_hidden_entries()
                        self.subhidden_entries.append(subfield)

    def append_hidden_entries(self):
        """reinsert hidden entries in form to allow for dynamiv lists
        """

        if self.hidden_entries is None:
            pass

        else:
            for subfield in self.subhidden_entries:
                subfield.append_hidden_entries()

            for field, hidden_entry in self.hidden_entries.items():

                field.entries.insert(0, hidden_entry)

            self.hidden_entries = None

    @staticmethod
    def get_field_data(field):

        def _get_field_data(field, nan_return):

            if field.data in NONES:
                return nan_return

            if isinstance(field, FileField):
                filename = secure_filename(field.data.filename)
                if filename in NONES:
                    return nan_return
                filepath = os.path.join(config['tmp_folder'], filename)
                field.data.save(filepath)
                return filepath

            return field.data

        if isinstance(field, BooleanField):
            return _get_field_data(field, False)
        else:
            return _get_field_data(field, None)

    def get_formatted(self):
        """get data from form and reformat for
        execution and saving
        """
        formatted_dict = {}
        for field in self:

            key = field.short_name

            if key == 'csrf_token':
                continue

            elif isinstance(field, FieldList):
                formatted_dict[key] = []

                for subfield in field:
                    if isinstance(subfield, FormField):
                        formatted_dict[key].append(subfield.get_formatted())

                    else:
                        formatted_dict[key].append(
                            self.get_field_data(subfield))

                # No Nones are allowed in a list, they will be removed
                # or the key will be set to None
                are_None = [value is None for value in formatted_dict[key]]

                if np.all(are_None):
                    formatted_dict[key] = None

                else:
                    formatted_dict[key] = [
                        value
                        for value in formatted_dict[key]
                        if value is not None]

            elif isinstance(field, FormField):
                formatted_dict[key] = field.get_formatted()

            else:
                formatted_dict[key] = self.get_field_data(field)

        return formatted_dict


class ManualLookupForm(NoCsrfForm, FormMixin):
    """parent class for manual lookup forms for instance checking.
    """
    pass


class ParentFormField(FormField):
    """FormField for a parent class for instance checking.
    """
    pass
