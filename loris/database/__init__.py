"""init for loris database
"""

import datajoint as dj
import os

os.environ['DJ_SUPPORT_ADAPTED_TYPES'] = "TRUE"


def conn(*args, **kwargs):
    """connect to database with hostname, username, and password.
    """
    dj.conn(*args, **kwargs)


# --- managing external file stores for database --- #
UBUNTU_LABSHARE = '/mnt/engram'
MAC_LABSHARE = '/Volumes/behnia-labshare'
FILESTORES = ('attachstore', 'datastore')

if 'stores' not in dj.config:
    dj.config['stores'] = {}

for filestore in FILESTORES:
    filestore_name = filestore
    # search if behnia labshare is connected
    if os.path.exists(UBUNTU_LABSHARE):
        filestore = os.path.join(UBUNTU_LABSHARE, filestore)
    elif os.path.exists(MAC_LABSHARE):
        filestore = os.path.join(MAC_LABSHARE, filestore)

    if not os.path.exists(filestore):
        os.makedirs(filestore)

    dj.config['stores'].update({
        filestore_name: {
            'protocol': 'file',
            'location': filestore
        }
    })


dj.config['enable_python_native_blobs'] = True
dj.config['enable_python_pickle_blobs'] = True
dj.config['enable_automakers'] = True
config = dj.config
