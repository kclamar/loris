"""script that is run as a subprocess when also wanting to insert
"""

import argparse
import sys
import os
import pickle

# add loris to path if not installed
try:
    from loris import config, conn
    conn()
except (ModuleNotFoundError, ImportError):
    filepath = __file__
    for i in range(4):
        filepath = os.path.dirname(filepath)
    sys.path.append(filepath)
    from loris import config, conn
    conn()

# import other loris packages
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.subprocess import Run
from loris.errors import LorisError
from loris.app.utils import datareader
from loris.database.schema.core import DataLookupName, FileLookupName


def get_insert_part_mixin(
    attr, value, lookup_name, lookup_table, attr_name,
    primary_dict,
    func=lambda x: x
):
    """get dictionary to insert from part table mixin (data or file)
    """
    lookup_name = {lookup_name: attr}
    if not (lookup_table & lookup_name):
        lookup_table.insert1(lookup_name)
    return {
        **primary_dict,
        **lookup_name,
        attr_name: func(value),
    }


def data_subclass(part_table, primary_dict):

    truth = (
        set(part_table.heading)
        == (set(primary_dict) | {'a_datum', 'data_lookup_name'}))
    # TODO test attr is blob and foreign key reference

    return truth


def file_subclass(part_table, primary_dict):

    truth = (
        set(part_table.heading)
        == (set(primary_dict) | {'a_file', 'file_lookup_name'}))
    # TODO test attr is blob and foreign key reference

    return truth


def inserting_autoscript_stuff(attr, value, table_class, primary_dict):
    """inserting data/file from autoscript into database
    """
    if attr.startswith('<') and attr.endswith('>'):
        # assumes either data or filemixin was used
        attr = attr.strip('<>')
        part_table_name, attr = attr.split(':')
        part_table = getattr(table_class, part_table_name)
        if data_subclass(part_table, primary_dict):
            to_insert = get_insert_part_mixin(
                attr, value, 'data_lookup_name', DataLookupName,
                'a_datum', primary_dict, func=datareader
            )
        elif file_subclass(part_table, primary_dict):
            to_insert = get_insert_part_mixin(
                attr, value, 'file_lookup_name', FileLookupName,
                'a_file', primary_dict
            )
        else:
            raise LorisError(f'part table {part_table.name} is not a '
                             'subclass of DataMixin or FilesMixin.')
        part_table.insert1(to_insert)
    elif attr in table_class.heading:
        if table_class.heading[attr].is_blob:
            value = datareader(value)
        (table_class & primary_dict).save_update(attr, value)
    else:
        raise LorisError(f'attr {attr} does not exist in '
                         f'table {table_class.full_table_name}')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--location", help="location of config file", type=str)
    parser.add_argument(
        "--tablename", help="name of table in database", type=str)
    parser.add_argument(
        "--script", help="filepath to script", type=str
    )
    parser.add_argument(
        "--outputfile", help="output file after running script", type=str
    )
    parser.add_argument(
        "--outputattr",
        help="attr in table for insertion of the output",
        type=str
    )
    parser.add_argument(
        "--configattr",
        help="attr in table for insertion of configuration",
        type=str
    )

    args = parser.parse_args()
    # TODO connect as user?

    with open(args.location, 'rb') as f:
        data = pickle.load(f)

    # get table class
    schema, table = args.tablename.split('.')
    table_class = getattr(config['schemata'][schema], table)
    dynamicform = DynamicForm(table_class)

    # reserve entry
    primary_dict = {}
    for key in table_class.primary_key:
        value = data['experiment_form'][key]
        primary_dict[key] = dynamicform.fields[key].format_value(value)

    print(f"Running autoscript for insertion with primary key: {primary_dict}")

    # reserve job for insertion
    jobs = config['schemata'][schema].schema.jobs
    jobs.reserve(
        table_class.full_table_name, primary_dict
    )

    try:
        with table_class.connection.transaction:
            dynamicform.insert(
                data['experiment_form'],
                check_reserved=False
            )

            command = [
                "python",
                "-u",
                f"{args.script}",
                "--location",
                f"{args.location}",
            ]

            process = Run()
            cwd = os.path.dirname(args.script)
            process.start(command, cwd)

            lnumbers = 0
            while True:
                length = len(process.lines)
                if length > lnumbers:
                    print(''.join(process.lines[lnumbers:length]))
                    lnumbers = length
                if process.p is not None and process.p.poll() is not None:
                    break

            if process.thread.is_alive():
                process.wait()

            if process.stdout is not None:
                print(process.stdout)

            if process.rc != 0:
                raise LorisError(f'automatic script error:\n{process.stderr}')

            # update/insert fields with data from autoscript
            if args.configattr != 'null' and args.configattr is not None:
                inserting_autoscript_stuff(
                    args.configattr, args.location,
                    table_class, primary_dict)
            if args.outputattr != 'null' and args.outputattr is not None:
                inserting_autoscript_stuff(
                    args.outputattr, os.path.join(cwd, args.outputfile),
                    table_class, primary_dict)
            # field name or <part_table_name:data/file_lookupname>
            # or just an attribute in the table
    except Exception as e:
        jobs.complete(
            table_class.full_table_name, primary_dict
        )
        raise e
    else:
        print(f"Finished autoscript for insertion with "
              f"primary key: {primary_dict}")
        jobs.complete(
            table_class.full_table_name, primary_dict
        )
