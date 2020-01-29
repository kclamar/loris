"""dabase-speific views
"""

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd

from loris import config
from loris.app.app import app
from loris.app.templates import form_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform
)
from loris.app.utils import (
    draw_helper, get_jsontable, save_join, user_has_permission)
from loris.app.login import User
from loris.database.users import grantuser, change_password


@app.route('/refresh')
@login_required
def refresh():
    app.session_refresh()
    return render_template('pages/refresh.html')


@app.route('/declare', methods=['GET', 'POST'])
@login_required
def declare():
    """declare a table
    """

    form = dynamic_tablecreationform(
        current_user.user_name
    )()

    return render_template(
        'pages/declare.html',
        form=form,
        url=url_for('declare'),
    )


@app.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    """join various tables in the database
    """

    formclass = dynamic_jointablesform()
    form = formclass()
    data = "None"

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit is None:
            pass

        elif submit in ['Submit']:
            if form.validate_on_submit():
                formatted_dict = form.get_formatted()

                try:
                    tables = []
                    for n, table_name in enumerate(formatted_dict['tables']):
                        tables.append(formclass.tables_dict[table_name])

                    joined_table = save_join(tables)
                    if formatted_dict['restriction'] is not None:
                        joined_table = (
                            joined_table & formatted_dict['restriction']
                        )
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    df = joined_table.fetch(format='frame').reset_index()
                    data = get_jsontable(df, joined_table.heading.primary_key)
                    flash(f"successfully joined tables.", 'success')

        form.append_hidden_entries()

    return render_template(
        'pages/join.html',
        form=form,
        url=url_for('join'),
        data=data,
        toggle_off_keys=[0]
    )
