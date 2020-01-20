"""views
"""

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from flask_dance.contrib.gitlab import gitlab
import datajoint as dj

from loris import config
from loris.app.app import app
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import dynamic_jointablesform
from loris.app.utils import draw_helper, get_jsontable, save_join


@app.route('/')
def home():
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))
    error = request.args.get('error', None)
    app.session_refresh()
    if error is not None:
        flash(error, 'error')
    return render_template('pages/home.html')


@app.route('/refresh')
def refresh():
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))
    error = request.args.get('error', None)
    app.session_refresh()
    if error is not None:
        flash(error, 'error')
    return render_template('pages/refresh.html')


@app.route('/about')
def about():
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))
    return render_template('pages/about.html')


@app.route(f"{config['tmp_folder']}/<path:filename>")
def tmpfile(filename):
    return send_from_directory(config['tmp_folder'], filename)


@app.route('/erd/', defaults={'schema': None}, methods=['GET', 'POST'])
@app.route('/erd/<schema>', methods=['GET', 'POST'])
def erd(schema):
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))

    filename = draw_helper(schema, type='schema')

    return render_template(
        'pages/erd.html', filename=filename,
        url=url_for('erd', schema=schema),
        schema=('ERD' if schema is None else schema)
    )


@app.route('/delete/<schema>/<table>',
           defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/delete/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
def delete(schema, table, subtable):
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))

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
            flash(f'Entry deleted: {_id}', 'error')
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


@app.route('/table/<schema>/<table>', defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/table/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
def table(schema, table, subtable):
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))
    # get id if it exists (will be restriction)
    _id = eval(request.args.get('_id', "None"))
    # get table and create dynamic form
    table_class = getattr(config['schemata'][schema], table)
    # get table name
    table_name = '.'.join([schema, table])

    # if not passed directly
    subtable = request.args.get('subtable', subtable)
    if not (subtable is None or subtable == 'None'):
        table_name = f'{table_name}.{subtable}'
        table_class = getattr(table_class, subtable)

    # standard delete and edit urls
    edit_url = url_for(
        'table', schema=schema, table=table, subtable=subtable)
    delete_url = url_for(
        'delete', schema=schema, table=table, subtable=subtable)

    dynamicform, form = config.get_dynamicform(
        table_name, table_class, DynamicForm
    )

    filename = dynamicform.draw_relations()

    # load/notload table
    data = dynamicform.get_jsontable(edit_url, delete_url)

    toggle_off_keys = [0]

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit is None:
            pass

        elif submit in ['Save', 'Overwrite']:
            if form.validate_on_submit():
                kwargs = {}
                if submit == 'Overwrite':
                    kwargs['replace'] = True

                try:
                    dynamicform.insert(form, **kwargs)
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    dynamicform.reset()
                    flash("Data Entered.")

        form.append_hidden_entries()

    elif _id is not None:
        edit = request.args.get('edit', "False")

        if edit == 'True':
            dynamicform.populate_form(_id, form)

    return render_template(
        'pages/form.html',
        form=form,
        data=data,
        table_name=table_name,
        url=url_for('table', table=table, schema=schema, subtable=subtable),
        toggle_off_keys=toggle_off_keys,
        filename=filename
    )


@app.route('/join', methods=['GET', 'POST'])
def join():
    if not gitlab.authorized:
        return redirect(url_for("gitlab.login"))

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
                    flash(f"successfully joined tables.")

        form.append_hidden_entries()

    return render_template(
        'pages/join.html',
        form=form,
        url=url_for('join'),
        data=data,
        toggle_off_keys=[0]
    )
