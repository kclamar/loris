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


@schema
class ColumnId(ManualLookup, dj.Manual):
    primary_comment = 'column id - e.g. A, B, or Home'


@schema
class SourceName(ManualLookup, dj.Manual):
    primary_comment = 'source of data - e.g. fruitflybrain'


@schema
class SynapticCounts(dj.Manual):
    definition = f"""
    -> CellType.proj(postsynaptic='cell_type')  # neuron receiving input - i.e. output cell
    -> ColumnId.proj(postsynaptic_column='column_id')
    -> CellType.proj(presynaptic='cell_type')  # neuron connecting to output cell - i.e. input cell
    -> ColumnId.proj(presynaptic_column='column_id')
    ---
    synaptic_count       : int unsigned
    count_percent = null   : double  # percent in terms of postsynaptic target
    -> [nullable] SourceName
    {COMMENTS}
    """
