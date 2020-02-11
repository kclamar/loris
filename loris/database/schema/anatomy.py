"""Anatomy Tables
"""

import datajoint as dj
from loris.database.schema.base import ManualLookup
from loris.database.attributes import lookupname

schema = dj.Schema('anatomy')


@schema
class NeuronSection(ManualLookup, dj.Manual):
    primary_comment = 'section of a neuron - e.g. dendrite, soma'


@schema
class BrainArea(ManualLookup, dj.Manual):
    primary_comment = 'brain area - e.g. medulla'


@schema
class CellType(ManualLookup, dj.Manual):
    primary_comment = 'standard cell type name - e.g. dm8'
