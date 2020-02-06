"""views for running analysis automatically
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
    PasswordForm, dynamic_tablecreationform, dynamic_runform
)
from loris.app.utils import (
    draw_helper, get_jsontable, save_join, user_has_permission)
from loris.app.login import User
from loris.database.users import grantuser, change_password


@app.route('/setup/<schema>/<table>', methods=['GET', 'POST'])
@login_required
def setup(schema, table):
    """setup a setting to run analysis
    """

    # TODO post method

    form = dynamic_settingstableform()()

    table_name = '.'.join([schema, table])
    url = url_for(
        'setup', schema=schema, table=table
    )
    # overwrite_url = url_for(
    #     'setup', schema=schema, table=table)
    delete_url = url_for(
        'delete', schema=schema, table=table
    )

    table_class = getattr(config['schemata'][schema], table).settings_table

    try:
        df = table_class.fetch(format='frame').reset_index()
    except Exception:
        df = table_class.proj(
            *table_class.heading.non_blobs
        ).fetch(format='frame').reset_index()

    # json table
    data = get_jsontable(
        df, table_class.primary_key,
        # overwrite_url=overwrite_url,
        delete_url=delete_url
    )

    # TODO populate form

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit in ['Save', 'Overwrite']:

            if form.validate_on_submit():
                kwargs = {}
                if submit == 'Overwrite':
                    kwargs['replace'] = True

                try:
                    formatted_dict = form.get_formatted()
                    table_class.insert1(
                        formatted_dict, **kwargs
                    )
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    flash(f"Data {submit} succeeded.", 'success')
                    return redirect(
                        url_for(
                            'setup',
                            table=table,
                            schema=schema,
                            # overwrite='True',
                            # _id=str(_id)
                        )
                    )

        form.append_hidden_entries()

    return render_template(
        'pages/setup.html',
        form=form,
        data=data,
        table_name=table_name,
        url=url,
        table=table,
        schema=schema,
        toggle_off_keys=[0]
    )


@app.route('/run/<schema>/<table>', methods=['GET', 'POST'])
@login_required
def run(schema, table):

    table_class = getattr(config['schemata'][schema], table)
    form = dynamic_runform(table_class)()
    table_name = '.'.join([schema, table])
    # TODO show relations

    return render_template(
        'pages/run.html',
        form=form,
        schema=schema,
        table=table,
        table_name=table_name
    )


@app.route('/plot/<schema>/<table>', methods=['GET', 'POST'])
@login_required
def plot(schema, table):
    return render_template('pages/home.html', user=current_user.user_name)
