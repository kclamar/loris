"""
"""

import os

from loris.settings import Config

os.environ['DJ_SUPPORT_ADAPTED_TYPES'] = "TRUE"

config = Config.load()
conn = config.conn
