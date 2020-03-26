"""factory for creating forms
"""

import pandas as pd
import numpy as np
import os
import graphviz
from flask_wtf import FlaskForm as Form
from flask import render_template, request, flash, url_for, redirect
import datajoint as dj
from datajoint.hash import key_hash
from datajoint.table import lookup_class_name
from wtforms import Form as NoCsrfForm
from wtforms import StringField, IntegerField, BooleanField, FloatField, \
    SelectField, FieldList, FormField, HiddenField

from loris.errors import LorisError
from loris import config
from loris.app.forms.dynamic_field import DynamicField
from loris.app.forms.formmixin import FormMixin, ParentFormField
from loris.app.utils import draw_helper, get_jsontable
from loris.utils import save_join


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

        self._set()

    def reset(self):
        """reset attributes and other operations not performed in init
        """

        self._set()

    def _set(self):
        """reset attributes
        """

        self._datatable = None
        self._joined_datatable_container = {}
        self._formclass = None
        self._restriction = None
        self._fields = None
        self._part_fields = None

    @property
    def fields(self):

        if self._fields is None:
            self._fields = self.get_fields()
        return self._fields

    @property
    def part_fields(self):

        if self._part_fields is None:
            self._part_fields = self.get_part_fields()
        return self._part_fields

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

    def get_fields(self):
        """get fields attributes
        """

        fields = {}

        for name, attr in self.table.heading.attributes.items():
            if name in self.skip:
                continue
            field = DynamicField(self.table, attr)
            fields[name] = field

        return fields

    def get_part_fields(self):
        """get part fields attribute
        """

        part_fields = {}

        for part_table in self.table.part_tables:
            # TODO aliased part tables
            dynamicform = self.__class__(
                part_table, skip=self.table.primary_key,
                formtype=NoCsrfForm
            )
            dynamicform.restriction = self.restriction
            part_fields[part_table.name] = dynamicform

        return part_fields

    def get_formclass(self):

        class TheForm(self.formtype, FormMixin):
            pass

        for name, field in self.fields.items():
            field = field.create_field()
            if field is not None:
                setattr(
                    TheForm,
                    name,
                    field
                )

        for part_name, part_form in self.part_fields.items():
            fieldlist = FieldList(
                FormField(
                    part_form.formclass
                ),
                min_entries=1
            )
            setattr(
                TheForm,
                part_name,
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
        joined_name=None,
        load_url=None
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
            overwrite_url=overwrite_url, name=self.table.name,
            load_url=load_url
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

        if isinstance(form, FormMixin):
            formatted_dict = form.get_formatted()
        elif isinstance(form, dict):
            formatted_dict = form
        else:
            raise LorisError(f'form is incorrect type (={type(form)}); '
                             'form must be dict or be a subclass of FormMixin')

        # check if replace in kwargs affects order of main and part helper
        replace = kwargs.get('replace', False)

        def main_helper(override_update_truth=False):
            primary_dict = self._insert(
                formatted_dict, _id,
                override_update_truth=override_update_truth,
                **kwargs
            )
            return primary_dict

        def part_helper(primary_dict):
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
                            key: part_form.fields[key].format_value(value)
                            for key, value in f_dict.items()
                            if (
                                key in part_form.table.primary_key
                                and key not in self.table.primary_key
                            )
                        }
                        _part_id = {**_id, **_part_primary}
                    # insert into part table
                    part_form._insert(
                        f_dict, _part_id, primary_dict,
                        override_update_truth=True,
                        **kwargs
                    )

        if self.table.connection.in_transaction:
            if replace and _id is not None:
                part_helper(_id)
                kwargs.pop('replace')
                primary_dict = main_helper(True)
            else:
                primary_dict = main_helper()
                part_helper(primary_dict)
        else:
            # perform operations within a transaction
            with self.table.connection.transaction:
                if replace and _id is not None:
                    part_helper(_id)
                    kwargs.pop('replace')
                    primary_dict = main_helper(True)
                else:
                    primary_dict = main_helper()
                    part_helper(primary_dict)
        return primary_dict

    def _insert(
        self, formatted_dict, _id=None,
        primary_dict=None, check_reserved=True,
        override_update_truth=False,
        **kwargs
    ):
        """insert helper function
        """

        insert_dict = {}

        for key, value in formatted_dict.items():
            if key in self.fields:
                insert_dict[key] = self.fields[key].format_value(value)

        if _id is None or kwargs.get('replace', False):
            truth = True
        else:
            restricted_table = self.table & _id
            if len(restricted_table) == 0:
                if override_update_truth:
                    truth = True
                else:
                    raise dj.DataJointError(
                        f'Entry {_id} does not exist; cannot update.'
                    )
            else:
                truth = False

        if primary_dict is not None:
            insert_dict = {**primary_dict, **insert_dict}

        primary_dict = {
            key: value for key, value in insert_dict.items()
            if key in self.table.primary_key
        }

        jobs = config['schemata'][self.table.database].schema.jobs

        if check_reserved:
            reserved = (
                jobs
                & {
                    'table_name': self.table.full_table_name,
                    'key_hash': key_hash(primary_dict)
                }
            )
            if reserved:
                raise dj.DataJointError(
                    f"Entry {primary_dict} has been reserved for table "
                    f"{self.table.full_table_name}; "
                    "change your primary key values."
                )

        if truth:
            try:
                self.table.insert1(insert_dict, **kwargs)
            except dj.DataJointError as e:
                raise dj.DataJointError(
                    "An error occured while inserting into table "
                    f"{self.table.full_table_name}: {e}"
                )
        else:  # editing entries savely
            # remove primary keys
            insert_dict = {
                key: value for key, value in insert_dict.items()
                if (
                    key not in self.table.primary_key
                    # skip updating non-specified files
                    # TODO fix for uploading files
                    and not (
                        value is None
                        and (
                            self.fields[key].attr.is_blob
                            or self.fields[key].attr.is_attachment
                        )
                    )
                )
            }
            if insert_dict:
                try:
                    restricted_table.save_updates(
                        insert_dict, reload=False
                    )
                except dj.DataJointError as e:
                    raise dj.DataJointError(
                        "An error occured while updating table "
                        f"{self.table.full_table_name}: {e}"
                    )

        return primary_dict

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
            ).proj(*part_table.heading.non_blobs).fetch(as_dict=True)
            # proj non_blobs?
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
