"""Equipment schema
"""

import datajoint as dj

from .base import PRIMARY_NAME, COMMENTS, DESCRIPTION, ManualLookup
from ..attributes import TrueBool, ZipFolder, Link

schema = dj.schema('equipment')

# custom attributes
bool = TrueBool()
folder = ZipFolder()
link = Link()


@schema
class PieceType(ManualLookup, dj.Manual):
    pass


@schema
class SystemType(ManualLookup, dj.Manual):
    pass


@schema
class System(dj.Manual):
    definition = f"""
    {PRIMARY_NAME.format(name='system_name')}
    ---
    -> [nullable] SystemType
    {DESCRIPTION}
    date_created : date # when was the system created
    active = 1 : <bool> # is the system active?
    system_data = null : blob@datastore # python objects for the whole system
    system_folder = null : <folder> # a complete folder to attach
    {COMMENTS}
    """

    class Piece(dj.Part):
        definition = f"""
        -> System
        piece_id = 1 : int
        ---
        -> [nullable] PieceType
        model_name : varchar(255)
        {DESCRIPTION}
        link = null : <link>
        piece_data = null : blob@datastore
        piece_file = null : attach@attachstore
        {COMMENTS}
        """
