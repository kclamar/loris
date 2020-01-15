"""Wtf Forms
"""

import numpy as np
# from flask_wtf import FlaskForm as Form
# from wtforms import Form as NoCsrfForm
from wtforms import FieldList, FormField, BooleanField


NONES = ['', None, 'None', 'null', 'NONE', np.nan]


class FormMixin:
    hidden_entries = None

    def populate_form(self, formatted_dict):
        """populate form from formatted_dict
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
                            sanitized_data = \
                                subfield.populate_form(idata).data
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

            if isinstance(field, FieldList):

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
            elif field.data is np.nan:
                return nan_return
            else:
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
        name = None  # if name stays None only return dict
        for field in self:

            key = field.short_name

            if key == 'csrf_token':
                continue

            elif key == '_name':
                name = field.data

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

        if name is None:
            return formatted_dict

        else:
            return formatted_dict, name
