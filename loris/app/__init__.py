"""
"""

import os

# storage of dynamic form
DYN_FORMS = {}

# data folder
config = {}
config['tmp_folder'] = '/tmp'

if not os.path.exists(config['tmp_folder']):
    os.makedirs(config['tmp_folder'])
