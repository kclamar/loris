"""fixed forms
"""

import pandas as pd
import numpy as np
import os
import glob
import graphviz
from flask_wtf import FlaskForm as Form
from wtforms import Form as NoCsrfForm
from flask import render_template, request, flash, url_for, redirect
import datajoint as dj
from datajoint.table import lookup_class_name
from wtforms import Form as NoCsrfForm
from wtforms import StringField, IntegerField, BooleanField, FloatField, \
    SelectField, FieldList, FormField, HiddenField, TextAreaField, PasswordField
from wtforms.validators import InputRequired, Optional, NumberRange, \
    ValidationError, Length, UUID, URL, Email, EqualTo

from loris import config
from loris.app.forms.formmixin import FormMixin, DynamicFileField, \
    DictField, ListField, JsonSerializableValidator, RestrictionField, \
    OptionalJsonSerializableValidator, Extension, CamelCaseValidator


RESTRICTION_DESCRIPTION = (
    'a sql where clause to apply to the joined '
    'table or a list of dicts or a dict of restrictions '
    '(do not include the WHERE command)'
)

RESTRICTION_LABEL = (
    'restriction - '
    '<a href="https://www.tutorialgateway.org/mysql-where-clause" '
    'target="_blank">help</a>'
)


class LoginForm(Form, FormMixin):
    user_name = StringField(
        'user name',
        description='SQL database username',
        validators=[InputRequired()]
    )
    password = PasswordField(
        'password',
        description='user password',
        validators=[InputRequired()]
    )


class SettingsNameForm(NoCsrfForm, FormMixin):
    settings_name = StringField(
        'settings name',
        description='save configuration under this name',
        validators=[InputRequired()]
    )


class PasswordForm(Form, FormMixin):
    old_password = PasswordField(
        'old password',
        description='old password',
        validators=[InputRequired()]
    )
    new_password = PasswordField(
        'new password',
        description='new password',
        validators=[InputRequired()]
    )
    repeat_password = PasswordField(
        'repeat password',
        description='repeat password',
        validators=[
            Length(min=10),
            InputRequired(),
            EqualTo('new_password', message='Passwords must match')
        ],
    )


class PartTableCreationForm(NoCsrfForm, FormMixin):
    table_name = StringField(
        'part table name',
        description='camel-case name of part table',
        validators=[
            InputRequired(),
            CamelCaseValidator()
        ]
    )
    definition = TextAreaField(
        'definition',
        description='datajoint definition of a part table',
        validators=[
            InputRequired(),
        ]
    )


def dynamic_autoscriptform():

    class AutoscriptForm(Form, FormMixin):
        autoscript = SelectField(
            'autoscript',
            description='autoscript',
            choices=[
                (ele, os.path.split(ele)[-1])
                for ele in
                glob.glob(os.path.join(config['autoscript_folder'], '*'))
            ],
            validators=[InputRequired()]
        )
        experiment = SelectField(
            'experiment',
            description='experiment',
            choices=[
                (ele, ele)
                for ele in
                config['autoscript_tables']
            ]
        )

    return AutoscriptForm


def dynamic_tablecreationform(user_name):

    class TableCreationForm(Form, FormMixin):
        schema = SelectField(
            'schema',
            description='schema',
            choices=[(key, key) for key in config.schemas_of_user(user_name)],
            default=user_name
        )
        table_name = StringField(
            'table name',
            description='camel-case name of table',
            validators=[
                InputRequired(),
                CamelCaseValidator()
            ]
        )
        table_type = SelectField(
            'table type',
            description='type of table',
            validators=[
                InputRequired()
            ],
            choices=[
                (ele, ele)
                for ele in [
                    'Manual', 'Imported', 'Computed',
                    'AutoImported', 'AutoComputed'
                ]
            ],
            default='Manual'
        )
        definition = TextAreaField(
            'definition',  # TODO add link
            description='datajoint definition of table',
            validators=[
                InputRequired(),
            ]
        )
        part_tables = FieldList(
            FormField(PartTableCreationForm),
            min_entries=1
        )

        @staticmethod
        def dynamic_table_class(table_name, table_type, definition_string):
            """dynamically create datajoint table
            """

            class TableClass(getattr(dj, table_type)):
                definition = definition_string
                name = table_name

            return TableClass

        def declare_table(self):
            """Create table
            """
            formatted_dict = self.get_formatted()

            schema = config['schemata'][formatted_dict['schema']].schema

            table_class = self.dynamic_table_class(
                formatted_dict['table_name'],
                formatted_dict['table_type'],
                formatted_dict['definition'])

            if formatted_dict['part_tables'] is not None:
                for part_table in formatted_dict['part_tables']:
                    part_table_class = self.dynamic_table_class(
                        part_table['table_name'],
                        'Part',
                        part_table['definition']
                    )

                    setattr(
                        table_class,
                        part_table['table_name'],
                        part_table_class
                    )

            # get complete context and declare table
            context = {
                **config['schemata'],
                **(config['schemata'][formatted_dict['schema']].__dict__
                   if schema.context is None else schema.context)
            }

            setattr(
                config['schemata'][formatted_dict['schema']],
                formatted_dict['table_name'],
                schema(table_class, context=context)
            )

    return TableCreationForm


def dynamic_jointablesform():

    class JoinTablesForm(Form, FormMixin):
        tables_dict = config['tables']
        tables = FieldList(
            SelectField(
                'tables',
                description='tables',
                choices=[(key, key) for key in tables_dict],
                validators=[InputRequired()]
            ),
            min_entries=1,
        )
        restriction = RestrictionField(
            RESTRICTION_LABEL,
            description=RESTRICTION_DESCRIPTION,
            validators=[Optional(), OptionalJsonSerializableValidator()],
            render_kw={
                'nullable': True
            }
        )

    return JoinTablesForm


class ModuleForm(NoCsrfForm, FormMixin):
    # TODO implement validators
    python_file = DynamicFileField(
        'python file',
        description='python file to upload with function',
        validators=[Optional(), Extension(['py'])]
    )
    python_module = StringField(
        'python module',
        description='name of python module, if no file is provided',
        validators=[Optional()],
        render_kw={
            'nullable': True
        }
    )

    def get_formatted(self):

        formatted_dict = super().get_formatted()

        if formatted_dict['python_file'] is None and formatted_dict['python_module'] is None:
            raise Exception('No python file or module was given.')
        elif formatted_dict['python_file']:
            return formatted_dict['python_file']
        else:
            return formatted_dict['python_module']


class FuncForm(NoCsrfForm, FormMixin):
    module = FormField(ModuleForm)
    function = StringField(
        'function',
        description='function name in the module',
        validators=[InputRequired()]
    )
    args = ListField(
        'args',
        description='list of arguments for init if function is class',
        validators=[Optional(), JsonSerializableValidator()],
        render_kw={
            'nullable': True
        }
    )
    kwargs = DictField(
        'kwargs',
        description='dict of keyword arguments for init if function is class',
        validators=[Optional(), JsonSerializableValidator()],
        render_kw={
            'nullable': True
        }
    )

    def get_formatted(self):

        formatted = super().get_formatted()

        if formatted['args'] is None and formatted['kwargs'] is None:
            return (
                formatted['module'],
                formatted['function']
            )
        else:
            return (
                formatted['module'],
                formatted['function'],
                ([] if formatted['args'] is None else formatted['args']),
                ({} if formatted['kwargs'] is None else formatted['kwargs'])
            )


def dynamic_settingstableform():

    class FetchTableForm(NoCsrfForm, FormMixin):
        table_name = SelectField(
            'table name',
            description='choose table',
            choices=[(table_name, table_name) for table_name in config['tables']],
            validators=[InputRequired()]
        )
        proj_list = ListField(
            'projections',
            description='arguments to project',
            validators=[Optional(), JsonSerializableValidator()],
            render_kw={
                'nullable': True
            }
        )
        proj_dict = DictField(
            'renamed projections',
            description='arguments to project and rename',
            validators=[Optional(), JsonSerializableValidator()],
            render_kw={
                'nullable': True
            }
        )

        def get_formatted(self):

            formatted = super().get_formatted()

            return {
                formatted['table_name'] : (
                    ([] if formatted['proj_list'] is None else formatted['proj_list']),
                    ({} if formatted['proj_dict'] is None else formatted['proj_dict'])
                )
            }

    class SettingstableForm(Form, FormMixin):
        settings_name = StringField(
            'settings name',
            description='unique name for settings used to autopopulate',
            validators=[InputRequired(), Length(max=63)]
        )
        description = TextAreaField(
            'description',
            description='longer description to describe settings',
            validators=[Optional(), Length(max=4000)],
            render_kw={
                'nullable': True
            }
        )
        func = FormField(FuncForm)
        global_settings = DictField(
            'global settings',
            description='dict of keyword arguments to pass to function for every entry',
            validators=[InputRequired(), JsonSerializableValidator()]
        )
        entry_settings = DictField(
            'entry settings',
            description='dict of keyword arguments to pass to function specific to each entry as defined by columns of the joined table',
            validators=[InputRequired(), JsonSerializableValidator()]
        )
        fetch_method = SelectField(
            'fetch method',
            description='method used to fetch data',
            choices=[('fetch1', 'fetch1'), ('fetch', 'fetch')],
        )
        fetch_tables = FieldList(
            FormField(FetchTableForm),
            label='fetch tables',
            min_entries=1,
            render_kw={
                'nullable': True
            }
        )
        restrictions = RestrictionField(
            RESTRICTION_LABEL,
            description=RESTRICTION_DESCRIPTION,
            validators=[Optional(), OptionalJsonSerializableValidator()],
            render_kw={
                'nullable': True
            }
        )
        parse_unique = ListField(
            'parse as unique',
            description='list of unique entries when using fetch - not wrapped into numpy.array',
            validators=[Optional(), JsonSerializableValidator()],
            render_kw={
                'nullable': True
            }
        )

        def get_formatted(self):

            formatted = super().get_formatted()

            formatted['fetch_tables'] = {
                key: value
                for table_dict in formatted['fetch_tables']
                for key, value in table_dict.items()
            }

            return formatted

    return SettingstableForm
