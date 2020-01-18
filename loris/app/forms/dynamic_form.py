"""factory for creating forms
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

from loris.app.forms.dynamic_field import DynamicField
from loris.app.forms.formmixin import FormMixin, ParentFormField
from loris.app.utils import draw_helper, get_jsontable


class DynamicForm:
    """creates forms from datajoint table class
    """

    def __init__(self, table, skip=[], formtype=Form):

        self._table = table
        self._skip = skip
        self._formtype = formtype

        self.reset()

    def reset(self):
        """reset attributes
        """

        self._datatable = None
        self._formclass = None
        self._restriction = None
        self._drawn = False
        self.fields = {}
        self.part_fields = {}

    @property
    def skip(self):
        return self._skip

    @property
    def formtype(self):
        return self._formtype

    @property
    def restriction(self):
        return self._restriction

    @restriction.setter
    def restriction(self, value):
        self._restriction = value

    @property
    def table(self):
        return self._table

    @property
    def datatable(self):

        if self._datatable is None:
            self._datatable = self.get_datatable()

        return self._datatable

    @property
    def formclass(self):

        if self._formclass is None:
            self._formclass = self.get_formclass()

        return self._formclass

    def get_formclass(self):

        class TheForm(self.formtype, FormMixin):
            pass

        for name, attr in self.table.heading.attributes.items():
            if name in self.skip:
                continue
            field = DynamicField(self.table, attr)
            self.fields[name] = field
            field = field.create_field()
            if field is not None:
                setattr(
                    TheForm,
                    name,
                    field
                )

        for part_table in self.table.part_tables:
            # TODO aliased part tables
            dynamicform = DynamicForm(
                part_table, skip=self.table.primary_key,
                formtype=NoCsrfForm
            )
            self.part_fields[part_table.name] = dynamicform
            fieldlist = FieldList(
                FormField(
                    dynamicform.formclass
                ),
                min_entries=1
            )
            setattr(
                TheForm,
                part_table.name,
                fieldlist
            )

        return TheForm

    @property
    def non_blobs(self):
        # TODO dealing with adapted attributes
        return self.table.heading.non_blobs

    def get_datatable(self):

        table = self.table

        if self.restriction is not None:
            table = table & self.restriction

        return table.proj(*self.non_blobs).fetch(
            format='frame', apply_adapter=False).reset_index()

    def get_jsontable(self, edit_url=None, delete_url=None):

        return get_jsontable(
            self.datatable, self.table.primary_key,
            edit_url=edit_url, delete_url=delete_url, name=self.table.name
        )

    def insert(self, form, **kwargs):
        """insert into datajoint table
        """

        formatted_dict = form.get_formatted()

        primary_dict = self._insert(formatted_dict, **kwargs)

        for part_name, part_form in self.part_fields.items():
            f_dicts = formatted_dict[part_name]
            if f_dicts is None:
                continue
            for f_dict in f_dicts:
                try:
                    part_form._insert(f_dict, primary_dict, **kwargs)
                except dj.DataJointError as e:
                    (self.table & primary_dict).delete(force=True)
                    raise e

    def _insert(self, formatted_dict, primary_dict=None, **kwargs):
        """formatted dict
        """

        insert_dict = {}

        for key, value in formatted_dict.items():
            if key in self.fields:
                insert_dict[key] = self.fields[key].format_value(value)

        if primary_dict is not None:
            insert_dict.update(primary_dict)

        self.table.insert1(insert_dict, **kwargs)

        return {
            key: value for key, value in insert_dict.items()
            if key in self.table.primary_key
        }

    def populate_form(self, restriction, form):

        formatted_dict = (
            self.table & restriction
        ).proj(*self.non_blobs).fetch1()

        for key, value in formatted_dict.items():
            formatted_dict[key] = self.fields[key].prepare_populate(value)

        # TODO populate part tables

        form.populate_form(formatted_dict)

    def update_foreign_fields(self, form):
        """update foreign fields with new information
        """

        for field in self.fields.values():
            field.update_foreign_field(form)

    def draw_relations(self):
        """draw relations
        """

        if self._drawn:
            return

        return draw_helper(self.table)
