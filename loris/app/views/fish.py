"""fish specific views
"""

import os
from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from ast import literal_eval
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd

from loris import config
from loris.app.app import app
from loris.app.templates import form_template, joined_table_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform
)
from loris.app.utils import draw_helper, get_jsontable, user_has_permission
from loris.utils import save_join
from loris.app.login import User
from loris.database.users import grantuser, change_password


@app.route('/genotype', methods=['GET', 'POST'])
@login_required
def genotype():
    schema = 'subjects'
    table = 'FishGenotype'
    subtable = None
    edit_url = url_for('genotype')
    overwrite_url = url_for('genotype')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='genotype',
        override_permissions=True
    )


@app.route('/entersubject', methods=['GET', 'POST'])
@login_required
def entersubject():
    schema = 'subjects'
    table = 'FishSubject'
    subtable = None
    edit_url = url_for('entersubject')
    overwrite_url = url_for('entersubject')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='entersubject',
        join_tables=[getattr(config['schemata'][schema], 'FishGenotype')],
        joined_name='subjectgenotype'
    )


@app.route('/subjectgenotype', methods=['GET', 'POST'])
@login_required
def subjectgenotype():
    """join various tables in the database
    """
    delete_url = url_for(
        'delete', schema='subjects', table='FishSubject', subtable=None)

    return joined_table_template(
        ['subjects.fish_genotype', 'subjects.fish_subject'],
        'Subject + Genotype Table',
        'entersubject',
        edit_url=url_for('entersubject'),
        delete_url=delete_url
    )
