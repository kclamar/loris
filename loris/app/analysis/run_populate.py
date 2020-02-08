"""run populate
"""

import argparse
import sys
import os
import json


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema", help="name of schema", type=str)
    parser.add_argument(
        "--table", help="name of table", type=str)
    parser.add_argument(
        "--kwargs", help="keyword arguments to pass to populate", type=str
    )

    args = parser.parse_args()
    # TODO connect as user?

    kwargs = json.loads(args.kwargs)

    # add loris to path if not installed
    try:
        from loris import config, conn
    except (ModuleNotFoundError, ImportError):
        filepath = __file__
        for i in range(4):
            filepath = os.path.dirname(filepath)
        print(filepath)
        sys.path.append(filepath)
        from loris import config, conn

    conn()

    table_class = getattr(
        config['schemata'][args.schema],
        args.table
    )

    table_class.populate(**kwargs)
