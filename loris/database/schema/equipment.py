"""Equipment schema
"""

import datajoint as dj

from loris.database.schema.base import PRIMARY_NAME, COMMENTS, DESCRIPTION, ManualLookup
from loris.database.schema.experimenters import Experimenter
from loris.database.attributes import truebool, tarfolder, link
from loris.database.attributes import lookupname


schema = dj.Schema('equipment')


@schema
class PieceType(ManualLookup, dj.Manual):
    primary_comment = 'type of piece - e.g. LED, dichroic'


@schema
class Manufacturer(ManualLookup, dj.Manual):
    primary_comment = 'name of manufacturer - e.g. ThorLabs, Semrock'


@schema
class SystemType(ManualLookup, dj.Manual):
    primary_comment = 'type of system - e.g. LED setup, ephys rig'


@schema
class System(dj.Manual):
    definition = f"""
    system_id : int auto_increment
    ---
    -> Experimenter
    -> SystemType
    date_created : date # when was the system created
    active = 1 : <truebool> # is the system active?
    system_data = null : blob@datastore # python objects for the whole system
    system_file = null : attach@attachstore # file(s) related to the system
    {DESCRIPTION}
    {COMMENTS}
    """

    class Piece(dj.Part):
        definition = f"""
        -> System
        piece_id = 1 : int # piece identification (integer)
        ---
        -> PieceType
        -> Manufacturer
        model_name : varchar(255) # standard model name by manufacturer
        link = null : <link>
        piece_data = null : blob@datastore # python objects for the piece
        piece_file = null : attach@attachstore # file(s) related to piece
        {DESCRIPTION}
        {COMMENTS}
        """
