"""Schema for Fish Subjects
"""

import datajoint as dj

from loris.database.schema.experimenters import Experimenter
from loris.database.schema.anatomy import CellType
from loris.database.schema.base import (
    ManualLookup, COMMENTS, PRIMARY_NAME, TAGS
)
from loris.database.attributes import chr, link, fishidentifier, crossschema
from loris.database.attributes import lookupname, tags


schema = dj.Schema('subjects')


@schema
class FishOrigin(ManualLookup, dj.Manual):
    primary_comment = 'where is the fish from? - e.g. Bloomington, Sarah'


@schema
class FishGenotype(dj.Manual):
    definition = f"""
    genotype_id : int auto_increment
    ---
    date_modified : date
    chr1 : <chr>
    chr2 : <chr>
    chr3 : <chr>
    chr4 = null : <chr>
    -> [nullable] CellType
    public_ids = null : <tags>
    {TAGS}
    {COMMENTS}
    """


@schema
class FishCross(dj.Manual):
    definition = f"""
    cross_id : int auto_increment
    ---
    date_modified : date
    -> Experimenter
    cross_schema = null : <crossschema>
    -> FishGenotype
    status = 'planned' : enum('planned', 'crossed', 'collecting', 'terminated')
    {COMMENTS}
    """


@schema
class StockGroup(ManualLookup, dj.Manual):
    primary_comment = 'stock group name - e.g. RBF'


@schema
class FishStock(dj.Manual):
    definition = f"""
    stock_id : int auto_increment
    ---
    -> FishGenotype
    -> Experimenter
    date_modified : date
    status = null : enum('dead', 'missing', 'instock', 'inpersonal', 'quarantine', 'recovery')
    priority = null : enum('1', '2')
    -> [nullable] FishOrigin
    -> [nullable] FishCross
    {COMMENTS}
    """


@schema
class RearingMethod(ManualLookup, dj.Manual):
    primary_comment = 'how the fish was raised - e.g. 25C, darkness'


@schema
class FishSubject(dj.Manual):
    definition = f"""
    subject_id : int auto_increment
    ---
    subject_name = null : varchar(255) # custom subject name -- not necessarily unique
    -> FishGenotype
    -> Experimenter
    -> [nullable] RearingMethod
    sex = 'U' : enum('F', 'M', 'U')
    age = null : float # age of fish in days
    prep_time = CURRENT_TIMESTAMP : timestamp # time of prep
    {TAGS}
    {COMMENTS}
    """
