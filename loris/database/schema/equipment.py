"""Equipment schema
"""

import datajoint as dj

from .base import PRIMARY_NAME, COMMENTS, DESCRIPTION, ManualLookup
from ..attributes import truebool, tarfolder, link

schema = dj.schema('equipment')


@schema
class PieceType(ManualLookup, dj.Manual):
    pass


@schema
class Manufacturer(ManualLookup, dj.Manual):
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
    active = 1 : <truebool> # is the system active?
    system_data = null : blob@datastore # python objects for the whole system
    system_file = null : attach@attachstore # a complete folder to attach
    {COMMENTS}
    """

    class Piece(dj.Part):
        definition = f"""
        -> System
        piece_id = 1 : int # piece identification (integer)
        ---
        -> [nullable] PieceType
        -> [nullable] Manufacturer
        model_name = null : varchar(255) # standard model name by manufacturer
        {DESCRIPTION}
        link = null : <link>
        piece_data = null : blob@datastore
        piece_file = null : attach@attachstore
        {COMMENTS}
        """
