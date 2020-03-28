"""
"""

import os

from loris.settings import Config
from loris.errors import LorisError

os.environ['DJ_SUPPORT_ADAPTED_TYPES'] = "TRUE"

config = Config.load()
conn = config.conn


import loris.dataframe as df
from loris.database.users import (
    grantuser, grantprivileges, dropuser, change_password
)

__all__ = [
    'config',
    'conn',
    'Config',
    'LorisError',
    'df',
    'grantuser',
    'grantprivileges',
    'dropuser',
    'change_password'
]

# if config['init_database']:
#     # import schema
#     from loris.database.schema import (
#         anatomy, equipment, experimenters,
#         imaging, recordings, subjects, core
#     )
#
#     __all__ += [
#         'anatomy', 'equipment', 'experimenters',
#         'imaging', 'recordings', 'subjects', 'core',
#     ]
