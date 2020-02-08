"""
"""

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd
import json
import os

from loris import config
from loris.app.app import app
from loris.app.templates import form_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform, dynamic_autoscriptform,
)
from loris.app.utils import (
    draw_helper, get_jsontable, save_join, user_has_permission)
from loris.app.login import User
from loris.database.users import grantuser, change_password
from loris.app.autoscripting.form_creater import dynamic_autoscripted_form
from loris.app.autoscripting.config_reader import ConfigReader
from loris.app.subprocess import Run


@app.route("/experiment",
           defaults={'table_name': None, 'autoscript_folder': None},
           methods=['GET', 'POST'])
@app.route("/experiment/<table_name>/<autoscript_folder>",
           methods=['GET', 'POST'])
@login_required
def experiment(table_name, autoscript_folder):

    _id = request.args.get('_id', None)
    folder = config['autoscript_folder']

    if autoscript_folder is not None and not autoscript_folder == 'None':
        autoscript_filepath = os.path.join(folder, autoscript_folder)
    else:
        autoscript_filepath = None

    reader = ConfigReader(autoscript_filepath, table_name,)
    if reader.initialized:
        enter_show = ['show', 'true']
    else:
        enter_show = ['', 'false']

    form = dynamic_autoscriptform()(prefix='load')

    submit = request.args.get('submit', None)

    process = config.get('subprocess', Run())

    process.check()

    if request.method == 'POST':

        reader.rm_hidden_entries()

        submit = request.form.get('submit', None)
        print(submit)

        if submit == 'Load' and form.validate_on_submit():
            autoscript_filepath = form.autoscript.data
            table_name = form.experiment.data

            return redirect(url_for(
                'experiment',
                autoscript_folder=os.path.split(autoscript_filepath)[-1],
                table_name=table_name))

        elif submit == 'Abort':
            process.abort()

        elif reader.initialized:
            if (
                (submit in reader.buttons)
                and reader.validate_on_submit(
                    submit,
                    flash_message=(
                        'Unable to run process; '
                        'check all fields in the forms')
                )
            ):
                reader.run(submit)

            elif (
                (submit == 'Save')
                and reader.validate_on_submit(
                    check_settings_name=True,
                    flash_message=(
                        'Unable to save settings; '
                        'check all fields in the forms')
                )
            ):
                reader.save_settings()

        # append hidden entries
        reader.append_hidden_entries()

    else:
        reader.populate_form(_id)

    return render_template(
        f'pages/experiment.html',
        form=form,
        data=reader.get_jsontable_settings(),
        toggle_off_keys=reader.toggle_off_keys,
        ultra_form=reader.ultra_form,
        buttons=reader.buttons,
        include_insert=reader.include_insert,
        enter_show=enter_show,
        url_experiment=url_for(
            'table',
            **{
                key: value
                for key, value in
                zip(('schema', 'table', 'subtable'), table_name.split('.'))
            }
        )
    )


@app.route("/deleteconfig/<table_name>/<autoscript_folder>",
           methods=['GET', 'POST'])
@login_required
def deleteconfig(table_name, autoscript_folder):

    redirect_url = request.args.get(
        'target',
        url_for(
            'experiment',
            table_name=table_name,
            autoscript_folder=autoscript_folder)
    )

    _id = request.args.get('_id', None)
    autoscript_filepath = os.path.join(
        config['autoscript_folder'], autoscript_folder
    )

    if _id is None:
        return redirect(redirect_url)

    reader = ConfigReader(autoscript_filepath, table_name,)

    name = reader.existing_settings[
        reader.existing_settings['_id'] == _id
    ]['name']

    if len(name) != 1:
        return redirect(redirect_url)

    name = name.iloc[0]

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        if submit == 'Delete':
            reader.delete_settings(_id, name)
        else:
            flash(f'Entry {name} was not deleted')
        return redirect(redirect_url)

    message = (
        f"Are you sure you want to delete configuration {name} "
        f"for protocol {autoscript_folder} and experiment type {table_name}?")

    return render_template(
        'pages/deleteconfig.html',
        message=message
    )
