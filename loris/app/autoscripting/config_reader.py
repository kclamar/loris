"""read config file class
"""

import os
import json
import pickle
import subprocess
import uuid
import datetime
import pandas as pd
import datajoint as dj
from flask import url_for, flash
from wtforms import Form as NoCsrfForm
from flask_wtf import FlaskForm as Form
from wtforms import FormField

from loris import config
from loris.app.utils import get_jsontable
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.formmixin import FormMixin
from loris.app.autoscripting.form_creater import dynamic_autoscripted_form
from loris.app.forms.fixed import SettingsNameForm
from loris.errors import LorisError
from loris.app.subprocess import Run


CURRENT_CONFIG = "_current_config.pkl"
SAVED_SETTINGS = "_saved_settings_{table_name}.json"
INSERT_SCRIPT = (
    f"{os.path.join(os.path.split(__file__)[0], 'run_insert_script.py')}"
)


class ConfigDynamicForm(DynamicForm):
    """changes default formtype
    """

    def __init__(self, table, skip=[], formtype=NoCsrfForm):
        super().__init__(table, skip, formtype)


class ConfigReader:
    """
    """

    def __init__(self, autoscript_filepath, table_name, **kwargs):

        if table_name is None or autoscript_filepath is None:
            self.experiment_form = "None"
            self.autoscript_forms = "None"
            self.buttons = "None"
            self.initialized = False
            self.ultra_form = "None"
            self.existing_settings = None
            self.autoscript_folder = None
            return

        self.initialized = True
        self.autoscript_folder = os.path.split(autoscript_filepath)[-1]
        self.autoscript_filepath = autoscript_filepath
        self.table_name = table_name
        self.saved_settings_file = os.path.join(
            autoscript_filepath, SAVED_SETTINGS.format(table_name=table_name))
        self.current_config_file = os.path.join(
            autoscript_filepath, CURRENT_CONFIG
        )
        if os.path.exists(self.saved_settings_file):
            self.existing_settings = pd.read_pickle(self.saved_settings_file)
        else:
            self.existing_settings = None

        schema, table = table_name.split('.')
        table_class = getattr(config['schemata'][schema], table)
        self.table_class = table_class

        # default recording id and subject id
        dynamicform, experiment_form = config.get_dynamicform(
            table_name, table_class, ConfigDynamicForm,
            **kwargs
        )
        dynamicform.reset()
        self.dynamicform = dynamicform
        self.experiment_form = experiment_form

        autoscript_forms, post_process_dict, buttons = \
            config.get_autoscriptforms(
                autoscript_filepath, table_name, dynamic_autoscripted_form,
                formclass=NoCsrfForm
            )
        self.autoscript_forms = autoscript_forms
        self.post_process_dict = post_process_dict
        self.buttons = buttons

        # dynamically create combined form
        class UltraForm(Form, FormMixin):
            table_name = self.table_class.name
            experiment_form = FormField(self.experiment_form.__class__)
            autoscript_forms = list(self.autoscript_forms.keys())
            settingsname_form = FormField(SettingsNameForm)

        for key, form in self.autoscript_forms.items():
            setattr(
                UltraForm,
                key,
                FormField(form)
            )

        self.ultra_form = UltraForm()
        # necessary currently to update experiment form in ultra form
        self.dynamicform.update_fields(self.ultra_form.experiment_form)

    def append_hidden_entries(self):

        if self.initialized:

            self.ultra_form.append_hidden_entries()

    def rm_hidden_entries(self):

        if self.initialized:

            self.ultra_form.rm_hidden_entries()

    def validate_on_submit(
        self, button=None,
        check_settings_name=False,
        flash_message=''
    ):
        """validate on submit on all forms (always check experiment form?)
        """
        truth = True

        if button is None:
            include = None
            check_experiment_form = True
        else:
            include = self.buttons[button].get('validate', [])
            if self.buttons[button].get('insert', False):
                check_experiment_form = True
            else:
                check_experiment_form = False

        if not self.ultra_form.is_submitted():
            flash(flash_message, 'error')
            return False

        if include is None:
            for key in self.ultra_form.autoscript_forms:
                truth = truth & getattr(self.ultra_form, key).form.validate()
        elif not include:
            pass
        else:
            for key in include:
                truth = truth & getattr(self.ultra_form, key).form.validate()

        if check_experiment_form:
            truth = truth & self.ultra_form.experiment_form.form.validate()

        if check_settings_name:
            truth = truth & self.ultra_form.settingsname_form.form.validate()

        if not truth:
            flash(flash_message, 'error')

        return truth

    def run(self, button):
        """run subprocess given the button key
        """

        # assert that script exists
        script = self.buttons[button].get('script')
        script_file = os.path.join(
            self.autoscript_filepath, script
        )

        assert os.path.exists(script_file), f'script {script} does not exist.'

        # get formatted form data and post_process
        keys = self.buttons[button].get('validate', [])
        data = {}
        for key in keys:
            idata = getattr(self.ultra_form, key).form.get_formatted()
            idata = self.post_process_dict[key](idata)
            data[key] = idata

        # add experiment_form
        data['experiment_form'] = (
            self.ultra_form.experiment_form.form.get_formatted()
        )
        # save configurations to pickle file
        with open(self.current_config_file, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

        process = config.get('subprocess', Run())

        if not process.running:

            if self.buttons[button].get('insert', False):
                # running the insert script
                command = [
                    "python",
                    "-u",
                    f"{INSERT_SCRIPT}",
                    "--tablename",
                    f"{self.table_name}",
                    "--script",
                    f"{script_file}",
                    "--location",
                    f"{self.current_config_file}",
                    "--outputfile",
                    f"{self.buttons.get('outputfile', 'null')}",
                    "--configattr",
                    f"{self.buttons.get('configattr', 'null')}",
                    "--outputattr",
                    f"{self.buttons.get('outputattr', 'null')}",
                ]
            else:
                # just run the python script
                command = [
                    "python",
                    "-u",
                    f"{script_file}",
                    "--location",
                    f"{self.current_config_file}",
                ]

            process.start(command, os.path.dirname(script_file))
            config['subprocess'] = process
            flash(f'running script {script}')
        else:
            flash(
                'Abort running subprocess before running a new process',
                'warning'
            )

    def save_settings(self):
        """save new settings to _save_settings.json - creates uuid
        for those settings
        """

        formatted_dict = self.ultra_form.get_formatted()

        settings_dict = {}
        settings_dict['_id'] = str(uuid.uuid4())
        settings_dict['name'] = formatted_dict['settingsname_form'][
            'settings_name'
        ]
        settings_dict['date'] = str(datetime.datetime.today())
        settings_dict['experiment_form'] = formatted_dict['experiment_form']

        for key in self.ultra_form.autoscript_forms:
            settings_dict[key] = formatted_dict[key]

        settings_dict = pd.Series(settings_dict)

        if self.existing_settings is None:
            self.existing_settings = pd.DataFrame([settings_dict])
        else:
            self.existing_settings = self.existing_settings.append(
                settings_dict,
                ignore_index=True,
            )

        self.existing_settings.to_pickle(self.saved_settings_file)

        flash(f'settings saved under {settings_dict["name"]}', 'success')

    def delete_settings(self, _id, name):
        """
        """

        if self.existing_settings is None:
            flash('No configurations exist', 'error')

        self.existing_settings = self.existing_settings[
            self.existing_settings['_id'] != _id
        ]

        self.existing_settings.to_pickle(self.saved_settings_file)
        flash(f'setting {name} successfully deleted', 'warning')

    def populate_form(self, _id):
        """populate form with settings table given uuid
        """

        if _id is None or not self.initialized:
            return

        selected_entries = self.existing_settings[
            self.existing_settings['_id'] == _id]

        if len(selected_entries) != 1:
            raise LorisError(f'entry id {_id} not in existing configurations.')

        settings_dict = selected_entries.iloc[0].to_dict()

        for name, field in self.dynamicform.fields.items():
            if field.is_integer:
                settings_dict['experiment_form'].pop(name, None)
            elif field.foreign_is_manuallookup:
                fk_field = settings_dict['experiment_form'].get(name, None)
                if fk_field is not None:
                    if fk_field['existing_entries'] == '<new>':
                        fk_value = fk_field.pop(name, None)
                        settings_dict['experiment_form'][name]['existing_entries'] = str(fk_value)

        self.ultra_form.populate_form(settings_dict)

        # TODO if auto-increment and foreign_key

    def get_jsontable_settings(
        self, page='experiment', deletepage='deleteconfig'
    ):
        """get jsontable for datatables
        """

        if not self.initialized or self.existing_settings is None:
            return "None"

        return get_jsontable(
            self.existing_settings,
            primary_key=None,
            load_url=url_for(
                page,
                table_name=self.table_name,
                autoscript_folder=self.autoscript_folder,
            ),
            delete_url=url_for(
                deletepage,
                table_name=self.table_name,
                autoscript_folder=self.autoscript_folder,
            )
        )

    def get_jsontable_form(self):

        if not self.initialized:
            return "None"

        return self.dynamicform.get_jsontable(
            delete_url=url_for(
                'delete',
                schema=self.table_class.database,
                table=self.table_class.name,
            ),
            edit_url=url_for(
                'table',
                schema=self.table_class.database,
                table=self.table_class.name
            )
        )

    @property
    def toggle_off_keys(self):
        """
        """

        if self.existing_settings is None:
            return

        length = len(self.existing_settings.columns)
        # just show name and date
        return [0] + [n+3 for n in range(length-3)]
