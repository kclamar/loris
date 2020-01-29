"""views
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User(form.user_name.data)
        if user.user_name == 'root':
            flash('Cannot login as root', 'error')
        elif not user.user_exists or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
        elif not user.is_active:
            flash(f'User {user.user_name} is an inactive member', 'error')
        elif form.password.data == config['standard_password']:
            flash('Please change your password', 'warning')
            login_user(user)
            # user_configs[user.user_name] = user.get_user_config(
            #     form.password.data)
            return redirect(url_for('change', user=user.user_name))
        else:
            login_user(user)
            # user_configs[user.user_name] = user.get_user_config(
            #     form.password.data)
            redirect_url = request.args.get('target', None)
            if redirect_url is None:
                return redirect(url_for('home'))
            else:
                return redirect(redirect_url)

    return render_template(
        'pages/login.html',
        form=form,
    )


@app.route("/logout")
@login_required
def logout():
    # user_configs.pop(current_user.user_name, None)
    logout_user()
    config.disconnect_ssh()
    flash('Successful logout!')
    return redirect(url_for('login'))


@app.route("/change", methods=['GET', 'POST'])
@login_required
def change():
    """change password
    """

    form = PasswordForm()

    if form.validate_on_submit():

        user = User(current_user.user_name)
        if (
            not user.user_exists
            or not user.check_password(form.old_password.data)
        ):
            flash('Old password incorrect', 'error')
        elif form.old_password.data == form.new_password.data:
            flash('New and old password match', 'error')
        else:
            change_password(current_user.user_name, form.new_password.data)
            # user_configs.pop(current_user.user_name, None)
            # user_configs.get_user_config(form.password.data)
            flash('Successfully changed password and logged in')
            login_user(user)

            redirect_url = request.args.get('target', None)
            if redirect_url is None:
                return redirect(url_for('home'))
            else:
                return redirect(redirect_url)

    return render_template(
        'pages/change.html',
        form=form
    )


@app.route('/')
@login_required
def home():
    # refresh session
    app.session_refresh()
    return render_template(
        'pages/home.html',
        user=current_user.user_name
    )


@app.route('/about')
@login_required
def about():
    return render_template('pages/about.html')


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():

    if current_user.user_name not in config['administrators']:
        flash("Only administrators are allowed to register users", "warning")
        return redirect(url_for('home'))

    user_class = config.user_table

    dynamicform, form = config.get_dynamicform(
        f'{config["user_schema"]}.{config["user_table"]}',
        user_class, DynamicForm
    )

    edit_url = url_for(
        'edit', schema=config['user_schema'], table=config['user_table'])
    delete_url = url_for(
        'delete', schema=config['user_schema'], table=config['user_table'])

    data = dynamicform.get_jsontable(
        edit_url, delete_url,
    )

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit == 'Register':
            if form.validate_on_submit():
                try:
                    dynamicform.insert(form)
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    dynamicform.reset()
                    formatted_dict = form.get_formatted()
                    grantuser(
                        formatted_dict[config['user_name']],
                        adduser=True
                    )
                    flash("User created", 'success')

        form.append_hidden_entries()

    return render_template(
        'pages/register.html',
        form=form,
        data=data,
        toggle_off_keys=[0]
    )


@app.route('/registergroup', methods=['GET', 'POST'])
@login_required
def registergroup():
    """setup a group
    """

    group_class = config.group_table

    dynamicform, form = config.get_dynamicform(
        f'{config["group_schema"]}.{config["group_table"]}',
        group_class, DynamicForm
    )

    edit_url = url_for(
        'edit', schema=config['group_schema'], table=config['group_table'])
    delete_url = url_for(
        'delete', schema=config['group_schema'], table=config['group_table'])

    data = dynamicform.get_jsontable(
        edit_url, delete_url,
    )

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit == 'Register':
            if form.validate_on_submit():
                try:
                    dynamicform.insert(form)
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    dynamicform.reset()
                    # formatted_dict = form.get_formatted()
                    # TODO create schema
                    # grantuser(
                    #     formatted_dict[config['user_name']],
                    #     adduser=True
                    # )
                    flash("Project group created", 'success')

        form.append_hidden_entries()

    return render_template(
        'pages/group.html',
        form=form,
        data=data,
        toggle_off_keys=[0]
    )


@app.route(f"{config['tmp_folder']}/<path:filename>")
@login_required
def tmpfile(filename):
    return send_from_directory(config['tmp_folder'], filename)
