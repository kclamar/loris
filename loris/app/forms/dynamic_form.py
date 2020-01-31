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
from loris.app.utils import draw_helper, get_jsontable, save_join


class DynamicForm:
    """creates forms from datajoint table class

    Parameters
    ----------
    table : class
        a subclass of datajoint.Table that is in the database.
    skip : list-like
        attributes to skip when creating form.
    formtype : class
        WTF form class or Flask form used to make a dynamic form subclass.
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
        self._joined_datatable_container = {}
        self._formclass = None
        self._restriction = None
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
    def joined_datatable_container(self):
        return self._joined_datatable_container

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
            dynamicform = self.__class__(
                part_table, skip=self.table.primary_key,
                formtype=NoCsrfForm
            )
            dynamicform.restriction = self.restriction
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

    def get_joined_datatable(self, tables, name=None):
        """join tables with self.table and return fetched joined
        table with primary key list.
        """

        if name in self.joined_datatable_container:
            return self.joined_datatable_container[name]

        joined_table = save_join([self.table]+tables)

        if self.restriction is not None:
            joined_table = joined_table & self.restriction

        datatable = joined_table.proj(
            *joined_table.heading.non_blobs
        ).fetch(
            format='frame', apply_adapter=False
        ).reset_index()

        if name is not None:
            self.joined_datatable_container[name] = \
                datatable, joined_table.primary_key

        return datatable, joined_table.primary_key

    def get_jsontable(
        self, edit_url=None, delete_url=None, overwrite_url=None,
        join_tables=None,
        joined_name=None
    ):

        if join_tables is not None:
            table, primary_key = self.get_joined_datatable(
                join_tables, joined_name
            )
        else:
            table = self.datatable
            primary_key = self.table.primary_key

        return get_jsontable(
            table, primary_key,
            edit_url=edit_url, delete_url=delete_url,
            overwrite_url=overwrite_url, name=self.table.name
        )

    def insert(self, form, _id=None, **kwargs):
        """insert into datajoint table

        Parameters
        ----------
        form : wtf.form from dynamicform.formclass
        _id : dict
            restriction for single entry (for save updating)
        kwargs : dict
            arguments passed to datajoint Table.insert function
        """

        formatted_dict = form.get_formatted()

        primary_dict = self._insert(formatted_dict, _id, **kwargs)

        for part_name, part_form in self.part_fields.items():
            f_dicts = formatted_dict[part_name]
            if f_dicts is None:
                continue
            for f_dict in f_dicts:
                if _id is None:
                    _part_id = None
                else:
                    # update with part entry that exist
                    _part_primary = {
                        key: value for key, value in f_dict.items()
                        if (
                            key in part_form.table.primary_key
                            and key not in self.table.primary_key
                        )
                    }
                    _part_id = {**_id, **_part_primary}
                # try insertion
                try:
                    part_form._insert(f_dict, _part_id, primary_dict, **kwargs)
                except dj.DataJointError as e:
                    raise dj.DataJointError(
                        *e.args,
                        (
                            'Error occured while entering data into part '
                            'table; master table entry already exists, and'
                            ' possibly some part table entries.'
                        )
                    )
                    # (self.table & primary_dict).delete(force=True)
                    # raise e

        return primary_dict

    def _insert(self, formatted_dict, _id=None, primary_dict=None, **kwargs):
        """insert helper function
        """

        insert_dict = {}

        for key, value in formatted_dict.items():
            if key in self.fields:
                insert_dict[key] = self.fields[key].format_value(value)

        if _id is None:
            truth = True
        else:
            restricted_table = self.table & _id
            if len(restricted_table) == 0:
                raise dj.DataJointError(
                    f'Entry {_id} does not exist; cannot update.'
                )
            truth = False

        if truth:
            if primary_dict is not None:
                insert_dict.update(primary_dict)

            self.table.insert1(insert_dict, **kwargs)

            return {
                key: value for key, value in insert_dict.items()
                if key in self.table.primary_key
            }
        else:  # editing entries savely
            # remove primary keys
            insert_dict = {
                key: value for key, value in insert_dict.items()
                if (
                    key not in self.table.primary_key
                    # skip updating non-specified files
                    # TODO
                    and not (
                        value is None
                        and (
                            self.fields[key].attr.is_blob
                            or self.fields[key].attr.is_attachment
                        )
                    )
                )
            }
            restricted_table.save_updates(
                insert_dict, reload=False
            )

    def populate_form(
        self, restriction, form, is_edit='False', **kwargs
    ):

        readonly = []

        formatted_dict = (
            self.table & restriction
        ).proj(*self.non_blobs).fetch1()  # proj non_blobs?

        for key, value in formatted_dict.items():
            formatted_dict[key] = self.fields[key].prepare_populate(value)

            if is_edit == 'True' and key in self.table.primary_key:
                readonly.append(key)

        # populate part tables
        for part_table in self.table.part_tables:
            part_formatted_list_dict = (
                part_table & restriction
            ).proj(*part_table.heading.non_blobs).fetch(as_dict=True)  # proj non_blobs?
            formatted_dict[part_table.name] = []
            for part_formatted_dict in part_formatted_list_dict:
                formatted_dict[part_table.name].append({})
                for key, value in part_formatted_dict.items():
                    if key in self.part_fields[part_table.name].fields:
                        formatted_dict[part_table.name][-1][key] = \
                            self.part_fields[
                                part_table.name
                            ].fields[key].prepare_populate(value)

                        if is_edit == 'True' and key in part_table.primary_key:
                            readonly.append(key)

        # update with kwargs
        formatted_dict.update(kwargs)

        form.populate_form(formatted_dict)
        return readonly

    def update_fields(self, form):
        """update foreign fields with new information
        """

        for field in self.fields.values():
            field.update_field(form)

    def draw_relations(self):
        """draw relations
        """

        return draw_helper(self.table)