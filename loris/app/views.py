"""views
"""

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
import datajoint as dj

from loris import config
from loris.app.app import app
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import dynamic_jointablesform
from loris.app.utils import draw_helper, get_jsontable, save_join


def ping(f):
    """Execute after each page refresh
    """

    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return redirect(url_for('home', error=str(e)))

    return wrapper


def session_refresh():
    config.refresh()
    # for testing when refresh happens
    print('refreshed!')
    session['schemata'] = list(config['schemata'].keys())


@app.route('/')
def home():
    error = request.args.get('error', None)
    session_refresh()
    if error is not None:
        flash(error, 'error')
    return render_template('pages/home.html')


@app.route('/about')
def about():
    return render_template('pages/about.html')


@app.route(f"{config['tmp_folder']}/<path:filename>")
def tmpfile(filename):
    return send_from_directory(config['tmp_folder'], filename)


@app.route('/erd/', defaults={'schema':None}, methods=['GET', 'POST'])
@app.route('/erd/<schema>', methods=['GET', 'POST'])
def erd(schema):

    if schema == 'ERD':
        schema = None

    filename = draw_helper(schema, type='schema')

    if schema is None:
        schema = 'ERD'

    return render_template(
        'pages/erd.html', filename=filename,
        url=url_for('erd', schema=schema),
        schema=schema
    )


@app.route('/delete/<schema>/<table>',
           defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/delete/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
def delete(schema, table, subtable):
    _id = eval(request.args.get('_id', "None"))
    raise NotImplementedError('delete')

    return render_template('pages/about.html')


@app.route('/table/<schema>/<table>', defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/table/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
def table(schema, table, subtable):
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
