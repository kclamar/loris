"""Anatomy Tables
"""

import datajoint as dj
from loris.database.schema.base import ManualLookup, PRIMARY_NAME, COMMENTS
from loris.database.attributes import lookupname, tags

schema = dj.Schema('anatomy')


@schema
class NeuronSection(ManualLookup, dj.Manual):
    primary_comment = 'section of a neuron - e.g. dendrite, soma'


@schema
class BrainArea(ManualLookup, dj.Manual):
    primary_comment = 'brain area - e.g. medulla'


@schema
class CellType(dj.Manual):
    definition = f"""
    {PRIMARY_NAME.format(name='cell_type', comment='standard cell type name - e.g. dm8')}
    ---
    neurotransmitters = null : <tags> # neurotransmitter of cell
    receptors = null : <tags> # receptors expressed by cell
    {COMMENTS}
    """
