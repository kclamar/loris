"""specific views for manipulating tables
"""


from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd
from ast import literal_eval

from loris import config
from loris.app.app import app
from loris.app.templates import form_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform
)
from loris.app.utils import draw_helper, get_jsontable, user_has_permission
from loris.utils import save_join
from loris.app.login import User
from loris.database.users import grantuser, change_password



@app.route('/delete/<schema>/<table>',
           defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/delete/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
@login_required
def delete(schema, table, subtable):

    redirect_url = request.args.get(
        'target',
        url_for(
            'table', schema=schema, table=table, subtable=subtable
        )
    )
    # get id if it exists (will be restriction)
    _id = literal_eval(request.args.get('_id', "None"))
    if (_id == 'None') or (_id is None):
        return redirect(redirect_url)

    # get table and create dynamic form
    table_class = getattr(config['schemata'][schema], table)
    # get table name
    table_name = '.'.join([schema, table])

    subtable = request.args.get('subtable', subtable)
    if not (subtable is None or subtable == 'None'):
        table_name = f'{table_name}.{subtable}'
        table_class = getattr(table_class, subtable)

    to_delete = table_class & _id
    # test if user is allowed to delete entry
    if not user_has_permission(to_delete, current_user.user_name):
        flash((
            f'User {current_user.user_name} is not'
            f' allowed to delete entry: {_id}'
        ), 'error')
        return redirect(redirect_url)
    message, commit_transaction, conn = to_delete._delete(force=True)

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        if submit == 'Delete' and commit_transaction:
            conn.commit_transaction()
            # reset table (will not cascade)
            dynamicform, form = config.get_dynamicform(
                table_name, table_class, DynamicForm
            )
            dynamicform.reset()
            # redired to table
            flash(f'Entry deleted: {_id}', 'warning')
            if redirect_url is None:
                return redirect(url_for(
                    'table',
                    schema=schema,
                    table=table,
                    subtable=subtable
                ))
            else:
                return redirect(redirect_url)

        elif submit == 'Cancel':
            conn.cancel_transaction()
            flash(f'Entry not deleted')
            return redirect(url_for(
                'table',
                schema=schema,
                table=table,
                subtable=subtable
            ))

    # always cancel transaction
    conn.cancel_transaction()

    if commit_transaction:
        return render_template(
            'pages/delete.html',
            table_name=table_name,
            message=message.splitlines(),
            restriction=str(_id),
            url=url_for(
                'table',
                schema=schema,
                table=table,
                subtable=subtable
            )
        )
    else:
        flash(message, 'error')
        return redirect(url_for(
            'table',
            schema=schema,
            table=table,
            subtable=subtable
        ))


@app.route('/table/<schema>/<table>',
           defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/table/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
@login_required
def table(schema, table, subtable):
    if (  # people can edit their entries but can't create new users
        (request.args.get('edit', None) != "True")
        and ((schema, table)
             == (config.user_table.database, config.user_table.name))
    ):
        return redirect(url_for('register'))
    elif (
        (schema, table)
        == (config.group_table.database, config.group_table.name)
    ):
        return redirect(url_for('registergroup'))
    elif (
        (schema, table)
        == (config.assigned_table.database, config.assigned_table.name)
    ):
        return redirect(url_for('assigngroup'))

    if (schema, table) == ('subjects', 'FishStock'):
        override_permissions = True
    else:
        override_permissions = False

    subtable = request.args.get('subtable', subtable)
    edit_url = url_for(
        'table', schema=schema, table=table, subtable=subtable)
    overwrite_url = url_for(
        'table', schema=schema, table=table, subtable=subtable)

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='table',
        override_permissions=override_permissions
    )
