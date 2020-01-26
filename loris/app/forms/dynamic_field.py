"""function for assigning fields
"""

import datetime
import os
import warnings
import pandas as pd
import numpy as np
import pickle
import json
import uuid

from datajoint.declare import match_type
from datajoint import FreeTable
from datajoint.table import lookup_class_name
from datajoint.utils import to_camel_case
from wtforms import BooleanField, SelectField, DateField, DateTimeField, \
    StringField, FloatField, IntegerField, FormField, \
    TextAreaField, FieldList, DecimalField
from wtforms.validators import InputRequired, Optional, NumberRange, \
    ValidationError, Length, UUID, URL, Email
from werkzeug.datastructures import FileStorage

from loris import config
from loris.utils import is_manuallookup
from loris.app.forms import NONES
from loris.app.forms.formmixin import ManualLookupForm, ParentFormField, \
    DynamicFileField, DictField, ListField, ParentValidator, JsonSerializableValidator, \
    AttachFileField, BlobFileField, Extension


class DynamicField:
    """Choose the right wtf field for each attribute in a datajoint Table

    Parameters
    ----------
    table : class
        datajoint.Table subclass representing a table in the mySQL database.
    attribute : dj.Attribute
        attribute in table to create a field for.
    ignore_foreign_fields : bool
        whether to process foreign keys to create foreign field forms or
        simply normal fields.
    """

    def __init__(self, table, attribute, ignore_foreign_fields=False):

        self._table = table
        self._attribute = attribute
        self._foreign_table = self.get_foreign_table()
        self._ignore_foreign_fields = ignore_foreign_fields

        # set default values
        self.is_uuid = False

    @property
    def ignore_foreign_fields(self):
        return self._ignore_foreign_fields

    @property
    def table(self):
        return self._table

    @property
    def attribute(self):
        return self._attribute

    @property
    def attr(self):
        return self._attribute

    @property
    def name(self):
        return self.attr.name

    @property
    def dependencies(self):
        """
        """

        if not (self.table.connection.dependencies):
            self.table.connection.dependencies.load()

        return self.table.connection.dependencies

    @property
    def is_foreign_key(self):
        """whether attribute is foreign key
        """
        return self.foreign_table is not None

    def get_foreign_table(self):
        """
        """
        parents = self.dependencies.parents(self.table.full_table_name)
        for table_name, table_info in parents.items():
            if self.name in table_info['attr_map']:
                # deal with aliasing
                if table_info['aliased']:
                    aliased_parents = self.dependencies.parents(table_name)
                    # aliased parent should only be one
                    table_name = list(aliased_parents)[0]
                break
        else:
            return None

        if self.table.declaration_context is not None:
            foreign_table = lookup_class_name(
                table_name, self.table.declaration_context
            )
            if foreign_table is not None:
                foreign_table = self.table.declaration_context[foreign_table]
        else:
            foreign_table = None

        if foreign_table is None:
            return FreeTable(self.table.connection, table_name)
        else:
            return foreign_table

    @property
    def foreign_table(self):
        return self._foreign_table

    @property
    def foreign_data(self):
        return self.foreign_table.proj(self.name).fetch()[self.name]

    @property
    def foreign_is_manuallookup(self):
        if not self.is_foreign_key:
            return False
        return is_manuallookup(self.foreign_table)

    def create_field(self):
        """create field for dynamic form
        """

        field = self._create_field()

        if field is None:
            warnings.warn(
                f'No field generated for {self.attr.name} of '
                f'type {self.attr.type}'
            )

        return field

    def _create_field(self, attr_type=None, kwargs=None):
        """create field for dynamic form
        """

        if attr_type is None:
            type = match_type(self.attr.type)
            sql_type = self.attr.sql_type
        else:
            sql_type = attr_type
            type = match_type(attr_type)

        if kwargs is None:
            kwargs = self.get_init_kwargs()

        if self.is_foreign_key and not self.ignore_foreign_fields:
            if self.foreign_is_manuallookup:
                return self.create_manuallookup_field(kwargs)
            elif len(self.foreign_data) <= config['fk_dropdown_limit']:
                return self.create_dropdown_field(kwargs)

        if type == 'INTEGER':
            return self.integer_field(kwargs)
        elif type == 'DECIMAL':
            return self.decimal_field(kwargs)
        elif type == 'FLOAT':
            return self.float_field(kwargs)
        elif type == 'STRING':
            return self.string_field(kwargs, sql_type)
        elif type == 'ENUM':
            return self.enum_field(kwargs, sql_type)
        elif type == 'BOOL':
            return self.bool_field(kwargs)
        elif type == 'TEMPORAL':
            return self.temporal_field(kwargs, sql_type)
        elif type in ('INTERNAL_BLOB', 'EXTERNAL_BLOB'):
            return self.blob_field(kwargs)
        elif type in ('INTERNAL_ATTACH', 'EXTERNAL_ATTACH'):
            return self.attach_field(kwargs)
        elif type == 'FILEPATH':
            return self.filepath_field(kwargs)
        elif type == 'UUID':
            return self.uuid_field(kwargs)
        elif type == 'ADAPTED':
            return self.adapted_field(kwargs)

    def get_init_kwargs(self):
        """get initialization dictionary to pass to field class
        """

        kwargs = {}
        kwargs['label'] = self.attr.name.replace('_', ' ')
        if self.attr.comment.strip():
            kwargs['description'] = self.attr.comment.strip()
        else:
            kwargs['description'] = self.attr.name.replace('_', ' ')

        nullable = self.attr.nullable or self.attr.default in NONES
        kwargs['render_kw'] = {
            'nullable': self.attr.nullable,
            'primary_key': self.attr.in_key
        }

        # ignore_foreign_fields assumes that a parent form is being created
        if nullable or self.ignore_foreign_fields:
            kwargs['default'] = None
        else:
            kwargs['default'] = self.attr.default

        if (
            (self.attr.in_key or not nullable)
            and not self.ignore_foreign_fields
        ):
            kwargs['validators'] = [InputRequired()]
        else:
            kwargs['validators'] = [Optional()]

        return kwargs

    def integer_field(self, kwargs):
        # auto increment integer primary keys
        if len(self.table()) == 0:
            kwargs['default'] = 1
        elif self.attr.in_key and len(self.table.heading.primary_key) == 1:
            kwargs['default'] = np.max(
                self.table.proj().fetch()[self.attr.name]
            ) + 1
        return IntegerField(**kwargs)

    def float_field(self, kwargs):
        return FloatField(**kwargs)

    def decimal_field(self, kwargs):
        # implement rounding correctly and use DecimalField
        return FloatField(**kwargs)

    def string_field(self, kwargs, sql_type):
        """creates a string field
        """
        max_length = int(sql_type.split('(')[-1][:-1])

        if sql_type.startswith('varchar'):
            kwargs['validators'].append(Length(max=max_length))
        elif sql_type.startswith('char'):
            kwargs['validators'].append(Length(min=max_length, max=max_length))
        else:
            return

        if max_length >= config['textarea_startlength']:
            return TextAreaField(**kwargs)
        else:
            return StringField(**kwargs)

    def temporal_field(self, kwargs, sql_type):
        """date and datetime field
        """

        if sql_type == 'datetime':
            kwargs['default'] = datetime.datetime.today()
            return DateTimeField(format='%Y-%m-%d %H:%M', **kwargs)
        elif sql_type == 'date':
            kwargs['default'] = datetime.date.today()
            return DateField(format='%Y-%m-%d', **kwargs)

    def enum_field(self, kwargs, sql_type):
        """create field for enum
        """
        choices = sql_type[sql_type.find('(')+1:sql_type.rfind(')')].split(',')
        choices = [ele.strip().strip('"').strip("'") for ele in choices]
        if self.attr.nullable:
            choices = ['NULL'] + choices
        kwargs['choices'] = [(ele, ele) for ele in choices]
        return SelectField(**kwargs)

    def bool_field(self, kwargs):
        if kwargs['default'] is None:
            kwargs['default'] = False
        elif kwargs['default']:
            kwargs['default'] = True
        else:
            kwargs['default'] = False
        # input always optional
        kwargs['validators'][0] = Optional()
        return BooleanField(**kwargs)

    def blob_field(self, kwargs):
        kwargs['validators'].append(Extension())
        return BlobFileField(**kwargs)

    def attach_field(self, kwargs):
        kwargs['validators'].append(Extension(config['attach_extensions']))
        return AttachFileField(**kwargs)

    def filepath_field(self, kwargs):
        # TODO implement
        # kwargs['validators'].append(FilePath())
        return

    def uuid_field(self, kwargs):
        self.is_uuid = True
        kwargs['validators'].append(Length(36, 36))
        kwargs['validators'].append(UUID())
        kwargs['default'] = str(uuid.uuid4())
        return StringField(**kwargs)

    def adapted_field(self, kwargs):
        """creates an adapted field type
        """

        try:
            attr_type = self.attr.adapter.attribute_type
        except NotImplementedError:
            attr_type = self.attr.sql_type

        attr_type_name = self.attr.type.strip('<>')
        adapter = config['custom_attributes'].get(attr_type_name, None)

        if adapter is None:
            pass
        elif attr_type_name == 'liststring':
            kwargs['validators'].append(JsonSerializableValidator)
            return ListField(**kwargs)
        elif attr_type_name == 'dictstring':
            kwargs['validators'].append(JsonSerializableValidator)
            return DictField(**kwargs)
        elif attr_type_name == 'link':
            kwargs['validators'].append(URL(False))
        elif attr_type_name == 'email':
            kwargs['validators'].append(Email())

        return self._create_field(attr_type, kwargs)

    def create_manuallookup_field(self, kwargs):
        """create a manual lookup field form.
        """

        kwargs['id'] = 'existing_entries'
        # TODO work with aliased foreign keys
        kwargs['validators'].insert(0, ParentValidator(self.name))

        # dynamically create form
        class FkForm(ManualLookupForm):
            parent_table_name = to_camel_case(self.foreign_table.table_name)
            existing_entries = self.create_dropdown_field(kwargs)

        for name, attr in self.foreign_table.heading.attributes.items():
            field = DynamicField(self.foreign_table, attr, True).create_field()
            if field is not None:
                setattr(
                    FkForm,
                    name,
                    field
                )

        return ParentFormField(FkForm)

    def create_dropdown_field(self, kwargs):
        """a simple drowndown field for foreign keys
        """

        choices = self.get_foreign_choices()
        if self.attr.nullable:
            kwargs['default'] = 'NULL'
        kwargs['choices'] = choices

        return SelectField(**kwargs)

    def get_foreign_choices(self):
        choices = [(str(ele), str(ele)) for ele in self.foreign_data]
        if self.attr.nullable:
            choices = [('NULL', 'NULL')] + choices
        if self.foreign_is_manuallookup:
            choices += [('<new>', '<add new entry>')]

        return choices

    def format_value(self, value):
        """format value
        """

        if self.foreign_is_manuallookup:
            if value['existing_entries'] == '<new>':
                value.pop('existing_entries')
                self.foreign_table.insert1(value)
                value = value[self.name]
            else:
                value = value['existing_entries']

        if self.attr.is_blob:
            if value in NONES:
                value = None
            elif value.endswith('npy'):
                value = np.load(value)
            elif value.endswith('csv'):
                value = pd.read_csv(value).to_records(False)
            elif value.endswith('pkl'):
                with open(value, 'rb') as f:
                    value = pickle.load(f)
            elif value.endswith('json'):
                with open(value, 'r') as f:
                    value = json.load(f)

        return value

    def prepare_populate(self, value):
        """format value for populating form
        """

        if self.foreign_is_manuallookup:
            value = {
                'existing_entries': value
            }

        if self.attr.is_blob and value is not None:
            # create filepath
            filepath = os.path.join(
                config['tmp_folder'],
                str(uuid.uuid4()) + '.pkl'
            )
            with open(filepath, 'wb') as f:
                pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)

            return filepath

        return value

    def update_field(self, form):

        if self.foreign_is_manuallookup:
            formfield = getattr(form, self.name)
            formfield.existing_entries.choices = self.get_foreign_choices()

            # update field if necessary
            self._update_field(formfield)

        elif self.is_foreign_key:
            field = getattr(form, self.name)
            field.choices = self.get_foreign_choices()

        else:
            self._update_field(form)

    def _update_field(self, form):

        if self.is_uuid:
            field = getattr(form, self.name)
            field.default = str(uuid.uuid4())
