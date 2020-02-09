"""script that is run as a subprocess when also wanting to insert
"""

import argparse
import sys
import os
import pickle

# add loris to path if not installed
try:
    from loris import config, conn
except (ModuleNotFoundError, ImportError):
    filepath = __file__
    for i in range(4):
        filepath = os.path.dirname(filepath)
    sys.path.append(filepath)
    from loris import config, conn
# import other loris packages
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.subprocess import Run
from loris.errors import LorisError
from loris.app.utils import datareader
from loris.database.schema.base import DataMixin, FilesMixin


def get_insert_part_mixin(
    attr, value, lookup_name, table_name, attr_name, func=lambda x: x
):
    """get dictionary to insert from part table mixin (data or file)
    """
    lookup_name = {lookup_name: attr}
    lookup_table = getattr(config['schemata']['core'], table_name)
    if not (lookup_table & lookup_name):
        lookup_table.insert1(lookup_name)
    return {
        **primary_dict,
        **lookup_name,
        attr_name: func(value),
    }


def inserting_autoscript_stuff(attr, value, table_class):
    """inserting data/file from autoscript into database
    """
    if attr.startswith('<') and attr.endswith('>'):
        # assumes either data or filemixin was used
        part_table_name, attr = attr.split(':')
        part_table = getattr(table_class, part_table_name)
        if issubclass(part_table, DataMixin):
            to_insert = get_insert_part_mixin(
                attr, value, 'data_lookup_name', 'DataLookupName',
                'a_datum', func=datareader
            )
        elif issubclass(part_table, FilesMixin):
            to_insert = get_insert_part_mixin(
                attr, value, 'file_lookup_name', 'FileLookupName',
                'a_file', func=datareader
            )
        else:
            raise LorisError('part table {part_table.name} is not a '
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

    # connect to database
    conn()

    # get table class
    schema, table = args.tablename.split('.')
    table_class = getattr(config['schemata'][schema], table)
    dynamicform = DynamicForm(table_class)

    # reserve entry
    primary_dict = {}
    for key in table_class.primary_key:
        value = data['experiment_form'][key]
        primary_dict[key] = dynamicform.fields[key].format_value(value)

    # reserve job for insertion
    jobs = config['schemata'][schema].schema.jobs
    jobs.reserve(
        table_class.full_table_name, primary_dict
    )

    with table_class.connection.transaction:
        primary_dict = dynamicform.insert(
            data['experiment_form'],
            check_reserved=False
        )

        command = [
            "python",
            f"{args.script}",
            "--location",
            f"{args.location}",
        ]

        process = Run()
        process(command)
        returncode, stdout, stderr = process.wait()

        if stdout is not None:
            print(stdout)

        if returncode != 0:
            raise LorisError(f'automatic script error:\n{stderr}')

        # update/insert fields with data from autoscript
        if args.configattr != 'null' and args.configattr is not None:
            inserting_autoscript_stuff(args.configattr, args.location, table_class)
        if args.outputattr != 'null' and args.outputattr is not None:
            inserting_autoscript_stuff(args.outputattr, args.outputfile, table_class)
        # field name or <part_table_name:data/file_lookupname>
        # or just an attribute in the table

    jobs.complete(
        table_class.full_table_name, primary_dict
    )

    # TODO insert into database
    # check if blob or attach for output and configuration saving
    # check if attributes in table
    # option with files/data part tables
    # use jobs table to reserve inserting this entry
