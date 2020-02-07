"""script that is run as a subprocess when also wanting to insert
"""

import argparse
import subprocess
import sys
import os


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

    command = [
        "python",
        f"{args.script}",
        "--location",
        f"{args.location}",
    ]

    p = subprocess.call(command, shell=False)

    # add loris to path if not installed
    try:
        from loris import config
    except (ModuleNotFoundError, ImportError):
        filepath = __file__
        for i in range(4):
            filepath = os.path.dirname(filepath)
        sys.path.append(filepath)
        from loris import config

    # TODO insert into database
    # check if blob or attach for output and configuration saving
    # check if attributes in table
    # option with files/data part tables
    # use jobs table to reserve inserting this entry
    raise NotImplementedError('inserting into database after running subprocess')
