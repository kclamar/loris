"""views
"""

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_dance.contrib.github import github
import datajoint as dj
import pandas as pd

from loris import config
from loris.app.app import app
from loris.app.templates import form_template
from loris.app.errors import LoginError
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import dynamic_jointablesform, dynamic_settingstableform
from loris.app.utils import draw_helper, get_jsontable, save_join
from loris.database.users import grantuser


def ping(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if not github.authorized:
            return redirect(url_for("github.login"))

        if ('ok' not in session) or ('authorized' not in session):
            # session authorized
            resp = github.get("/user")
            session['ok'] = resp.ok
            # raise error here already
            if not session['ok']:
                session['user'] = None
                session['authorized'] = False
                raise LoginError(2)

            # get experimenter class
            Experimenter = getattr(
                config['schemata']['experimenters'],
                'Experimenter'
            )

            # user of session
            user = resp.json()['login']
            session['authorized'] = (
                user
                in Experimenter.proj().fetch()['experimenter']
            )
            session['user'] = user

        if not session['ok']:
            raise LoginError(2)

        elif not session['authorized']:
            raise LoginError(1)

        return f(*args, **kwargs)

    return wrapper


@app.route('/')
@ping
def home():
    # refresh session
    app.session_refresh()
    return render_template(
        'pages/home.html',
        user=session['user']
    )


@app.route("/logout")
def logout():
    config.disconnect_ssh()
    return render_template('pages/logout.html')


@app.route('/refresh')
@ping
def refresh():
    app.session_refresh()
    return render_template('pages/refresh.html')


@app.route('/about')
@ping
def about():
    return render_template('pages/about.html')


@app.route('/register', methods=['GET', 'POST'])
@ping
def register():

    Experimenter = getattr(config['schemata']['experimenters'], 'Experimenter')

    dynamicform, form = config.get_dynamicform(
        'experimenters.Experimenter',
        Experimenter, DynamicForm
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
                    connection = '{host}:{port}'.format(
                        **config['connection'].conn_info
                    )
                    grantuser(
                        formatted_dict['experimenter'],
                        connection=connection,
                        adduser=True
                    )
                    flash("User created.", 'success')

        form.append_hidden_entries()

    return render_template(
        'pages/register.html',
        form=form
    )


@app.route(f"{config['tmp_folder']}/<path:filename>")
@ping
def tmpfile(filename):
    return send_from_directory(config['tmp_folder'], filename)


@app.route('/erd/', defaults={'schema': None}, methods=['GET', 'POST'])
@app.route('/erd/<schema>', methods=['GET', 'POST'])
@ping
def erd(schema):

    only_essentials = eval(request.args.get('only_essentials', 'False'))

    filename = draw_helper(
        schema, type='schema', only_essentials=only_essentials
    )

    return render_template(
        'pages/erd.html', filename=filename,
        url=url_for('erd', schema=schema),
        schema=('ERD' if schema is None else schema),
    )


@app.route('/delete/<schema>/<table>',
           defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/delete/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
@ping
def delete(schema, table, subtable):

    redirect_url = request.args.get('target', None)
    # get id if it exists (will be restriction)
    _id = eval(request.args.get('_id', "None"))
    if _id == 'None':
        return redirect(url_for(
            'table', schema=schema, table=table, subtable=subtable
        ))
    # get table and create dynamic form
    table_class = getattr(config['schemata'][schema], table)
    # get table name
    table_name = '.'.join([schema, table])

    to_delete = table_class & _id
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
            flash(f'Entry not deleted')
            return redirect(url_for(
                'table',
                schema=schema,
                table=table,
                subtable=subtable
            ))

    if commit_transaction:
        conn.cancel_transaction()
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


@app.route('/setup/<schema>/<table>', methods=['GET', 'POST'])
@ping
def setup(schema, table):

    form = dynamic_settingstableform()()

    table_name = '.'.join([schema, table])
    url = url_for(
        'setup', schema=schema, table=table
    )
    overwrite_url = url_for(
        'setup', schema=schema, table=table)
    delete_url = url_for(
        'delete', schema=schema, table=table
    )

    table_class = getattr(config['schemata'][schema], table).settings_table

    try:
        df = table_class.fetch(format='frame').reset_index()
    except:
        df = table_class.proj(
            *table_class.heading.non_blobs
        ).fetch(format='frame').reset_index()

    # json table
    data = get_jsontable(
        df, table_class.primary_key, overwrite_url=overwrite_url,
        delete_url=delete_url
    )

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


@app.route('/table/<schema>/<table>', defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/table/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
@ping
def table(schema, table, subtable):
    subtable = request.args.get('subtable', subtable)
    edit_url = url_for(
        'edit', schema=schema, table=table, subtable=subtable)
    overwrite_url = url_for(
        'table', schema=schema, table=table, subtable=subtable)

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='table',
    )


@app.route('/edit/<schema>/<table>', defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/edit/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
@ping
def edit(schema, table, subtable):
    subtable = request.args.get('subtable', subtable)
    edit_url = url_for(
        'edit', schema=schema, table=table, subtable=subtable)
    overwrite_url = url_for(
        'table', schema=schema, table=table, subtable=subtable)

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='edit',
        redirect_page='table'
    )


@app.route('/run/<schema>/<table>', methods=['GET', 'POST'])
@ping
def run(schema, table):
    return render_template('pages/home.html', user=session['user'])


@app.route('/plot/<schema>/<table>', methods=['GET', 'POST'])
@ping
def plot(schema, table):
    return render_template('pages/home.html', user=session['user'])


@app.route('/genotype', methods=['GET', 'POST'])
@ping
def genotype():
    schema = 'subjects'
    table = 'FlyGenotype'
    subtable = None
    edit_url = url_for('genotype')
    overwrite_url = url_for('genotype')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='genotype',
    )


@app.route('/stock', methods=['GET', 'POST'])
@ping
def stock():
    schema = 'subjects'
    table = 'FlyStock'
    subtable = None
    edit_url = url_for('stock')
    overwrite_url = url_for('stock')

    # # get table
    # table_class = getattr(config['schemata'][schema], table)
    # table_class & {'stock_group': 'common'}
    # existing_ids = pd.Series(
    #     table_class.proj().fetch()['stock_name']
    # ).str.replace(
    #     '[^0-9]', '' # replaces any characters that are not a number
    # ).astype(int)
    # new_id = existing_ids.max() + 1
    # if pd.isnull(new_id):
    #     new_id = 1
    # stock_name = f'{config["stock_prefix"]}{new_id}'

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='stock',
        join_tables=[getattr(config['schemata'][schema], 'FlyGenotype')],
        joined_name='stockgenotype',
        # stock_name=stock_name
    )


@app.route('/cross', methods=['GET', 'POST'])
@ping
def cross():
    schema = 'subjects'
    table = 'FlyCross'
    subtable = None
    edit_url = url_for('cross')
    overwrite_url = url_for('cross')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='cross',
        join_tables=[getattr(config['schemata'][schema], 'FlyGenotype')],
        joined_name='crossgenotype'
    )


@app.route('/join', methods=['GET', 'POST'])
@ping
def join():

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
