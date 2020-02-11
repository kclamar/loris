"""tables for recording schema
"""

import datajoint as dj
from loris.database.schema.base import ManualLookup
from loris.database.attributes import lookupname


schema = dj.Schema('recordings')


@schema
class RecordingType(ManualLookup, dj.Manual):
    primary_comment = 'type of recording - e.g. TSeries, ZStack'


@schema
class RecordingSolution(ManualLookup, dj.Manual):
    primary_comment = 'type of solution - e.g. saline, saline + OA'
