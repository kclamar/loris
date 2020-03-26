"""
"""

import os

from loris.settings import Config
import loris.database as db
import loris.database.schema as schema
from loris.errors import LorisError

os.environ['DJ_SUPPORT_ADAPTED_TYPES'] = "TRUE"

config = Config.load()
conn = config.conn


import loris.dataframe as df

__all__ = [
    'db',
    'config',
    'conn',
    'Config',
    'schema',
    'LorisError',
    'df'
]

if config['init_database']:
    from loris.database.schema import (
        anatomy, equipment, experimenters,
        imaging, recordings, subjects, core
    )

    __all__ += [
        'anatomy', 'equipment', 'experimenters',
        'imaging', 'recordings', 'subjects', 'core'
    ]
