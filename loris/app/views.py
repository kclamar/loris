"""views
"""

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
import datajoint as dj

from . import DYN_FORMS, config
from .app import app
from .virtual_schema import schemata
from .forms.dynamic_form import DynamicForm
from .utils import draw_helper


@app.route('/')
def home():
    session['schemata'] = list(schemata.keys())
    return render_template('pages/home.html')


@app.route('/about')
def about():
    return render_template('pages/about.html')


@app.route('/tmp/<path:filename>')
def tmpfile(filename):
    return send_from_directory(config['tmp_folder'], filename)

@app.route('/erd/', defaults={'schema':None}, methods=['GET', 'POST'])
@app.route('/erd/<schema>', methods=['GET', 'POST'])
def erd(schema):
    return render_template(
        'pages/erd.html', filename=draw_helper(schema, type='schema'),
        url=url_for('erd', schema=schema),
        schema=('ERD' if schema is None else schema)
    )


@app.route('/delete/<schema>/<table>', defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/delete/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
def delete(schema, table, subtable):
    _id = eval(request.args.get('_id', "None"))
    print(_id)
    print(type(_id))

    return render_template('pages/about.html')


@app.route('/table/<schema>/<table>', defaults={'subtable': None}, methods=['GET', 'POST'])
@app.route('/table/<schema>/<table>/<subtable>', methods=['GET', 'POST'])
def table(schema, table, subtable):
    # get id if it exists (will be restriction)
    _id = eval(request.args.get('_id', "None"))
    # get table and create dynamic form
    table_class = getattr(schemata[schema], table)
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

    if table_name not in DYN_FORMS:
        dynamicform = DynamicForm(table_class)
        form = dynamicform.formclass()
        DYN_FORMS[table_name] = dynamicform
    else:
        # update foreign keys
        dynamicform = DYN_FORMS[table_name]
        form = dynamicform.formclass()
        dynamicform.update_foreign_fields(form)

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
