"""script that is run as a subprocess when also wanting to insert
"""

import argparse
import subprocess
import sys
import os
import pickle


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--location", help="location of basedir", type=str)
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

    # add loris to path if not installed
    try:
        from loris import config, conn
    except (ModuleNotFoundError, ImportError):
        filepath = __file__
        for i in range(4):
            filepath = os.path.dirname(filepath)
        sys.path.append(filepath)
        from loris import config, conn

    # connect to database
    conn()

    from loris.app.forms.dynamic_form import DynamicForm
    from loris.app.subprocess import Run
    from loris.errors import LorisError

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
        returncode = process.wait()

        if returncode != 0:
            raise LorisError(f'automatic script error: {returncode}')

        # update fields with data from autoscript
        args.outputattr  # field name or <datamixin_name>, <filemixin_name>
        args.configattr  # field name or <datamixin_name>, <filemixin_name>
        args.outputfile  # for data can be - npy, csv, json, pkl, txt

    jobs.complete(
        table_class.full_table_name, primary_dict
    )

    # TODO insert into database
    # check if blob or attach for output and configuration saving
    # check if attributes in table
    # option with files/data part tables
    # use jobs table to reserve inserting this entry
