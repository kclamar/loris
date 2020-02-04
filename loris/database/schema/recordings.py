"""tables for recording schema
"""

import datajoint as dj
from loris.database.schema.base import ManualLookup

schema = dj.schema('recordings')


@schema
class RecordingType(ManualLookup, dj.Manual):
    primary_comment = 'type of recording - e.g. TSeries, ZStack'


@schema
class ProtocolType(ManualLookup, dj.Manual):
    primary_comment = 'type of protocol - e.g. Dreye, MARGO, Motyxia'


@schema
class RecordingSolution(ManualLookup, dj.Manual):
    primary_comment = 'type of solution - e.g. saline, saline + OA'
