"""Anatomy Tables
"""

import datajoint as dj
from loris.database.schema.base import ManualLookup, PRIMARY_NAME, COMMENTS
from loris.database.attributes import lookupname, tags

schema = dj.Schema('anatomy')


@schema
class BrainArea(ManualLookup, dj.Manual):
    primary_comment = 'brain area - e.g. medulla'
