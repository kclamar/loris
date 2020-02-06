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


CURRENT_CONFIG = "_current_config.pkl"
SAVED_SETTINGS = "_saved_settings_{table_name}.json"


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
            self.include_insert = False
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
            autoscript_filepath, SAVED_SETTINGS)
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
        self.dynamicform = dynamicform
        self.experiment_form = experiment_form

        autoscript_forms, post_process_dict, buttons, include_insert = \
            config.get_autoscriptforms(
                autoscript_filepath, table_name, dynamic_autoscripted_form,
                formclass=NoCsrfForm
            )
        self.autoscript_forms = autoscript_forms
        self.post_process_dict = post_process_dict
        self.buttons = buttons
        self.include_insert = include_insert

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

    def append_hidden_entries(self):

        if self.initialized:

            self.ultra_form.append_hidden_entries()

    def rm_hidden_entries(self):

        if self.initialized:

            self.ultra_form.rm_hidden_entries()

    def validate_on_submit(
        self, include=None, check_experiment_form=False,
        check_settings_name=False, flash_message=''
    ):
        """validate on submit on all forms (always check experiment form?)
        """
        truth = True

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
        script = self.buttons[button][0]
        script_file = os.path.join(
            self.autoscript_filepath, script
        )

        assert os.path.exists(script_file), f'script {script} does not exist.'

        # get formatted form data and post_process
        keys = self.buttons[button][1]
        data = {}
        for key in keys:
            idata = getattr(self.ultra_form, key).form.get_formatted()
            idata = self.post_process_dict[key](idata)
            data[key] = idata

        # save configurations to pickle file
        with open(self.current_config_file, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

        p = config.get('subprocess', None)

        if p is None or p.poll() is not None:
            p = subprocess.Popen(
                [
                    "python",
                    f"{script_file}",
                    "--location",
                    f"{self.current_config_file}",
                ],
                shell=False
            )
            config['subprocess'] = p
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
        settings_dict['date'] = str(datetime.date.today())
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
            raise Exception(f'entry id {_id} not in existing configurations.')

        settings_dict = selected_entries.iloc[0].to_dict()
        self.ultra_form.populate_form(settings_dict)

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

    @property
    def toggle_off_keys(self):
        """
        """

        if self.existing_settings is None:
            return

        length = len(self.existing_settings.columns)
        # just show name and date
        return [0] + [n+3 for n in range(length-3)]

    def insert(self, **kwargs):
        """
        """

        # TODO inserting configurations data into protocol_data field?

        try:
            self.dynamicform.insert(
                self.ultra_form.experiment_form.form,
                **kwargs
            )
        except dj.DataJointError as e:
            flash(f'{e}', 'error')
        else:
            self.dynamicform.reset()
            flash(f"Data inserted into database", 'success')
