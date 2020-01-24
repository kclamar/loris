"""Schema for Fly Subjects
"""

import datajoint as dj

from loris.database.schema.experimenters import Experimenter
from loris.database.schema.base import ManualLookup, COMMENTS, PRIMARY_NAME
from loris.database.attributes import chr, link, flyidentifier, crossschema


schema = dj.schema('subjects')


@schema
class CellType(ManualLookup, dj.Manual):
    primary_comment = 'standard cell type name - e.g. dm8'


@schema
class FlyOrigin(ManualLookup, dj.Manual):
    primary_comment = 'where is the fly from? - e.g. Bloomington, Sarah'


@schema
class FlyGenotype(dj.Manual):
    definition = f"""
    genotype_id : int auto_increment
    ---
    date_modified : date
    chr1 : <chr>
    chr2 : <chr>
    chr3 : <chr>
    chr4 = null : <chr>
    -> [nullable] CellType
    {COMMENTS}
    """

    class PublicIdentifier(dj.Part):
        definition = """
        -> FlyGenotype
        identifier : <flyidentifier> # public identifier
        ---
        link = null : <link>
        """


@schema
class FlyCross(dj.Manual):
    definition = f"""
    cross_id : int auto_increment
    ---
    date_modified : date
    -> Experimenter
    cross_schema = null : <crossschema>
    -> FlyGenotype
    status = 'planned' : enum('planned', 'crossed', 'collecting', 'terminated')
    {COMMENTS}
    """


@schema
class StockGroup(ManualLookup, dj.Manual):
    primary_comment = 'stock group name - e.g. RBF'


@schema
class FlyStock(dj.Manual):
    definition = f"""
    stock_id : int auto_increment
    ---
    -> FlyGenotype
    -> Experimenter
    date_modified : date
    status = null : enum('dead', 'missing', 'instock', 'inpersonal', 'quarantine', 'recovery')
    -> [nullable] FlyOrigin
    -> [nullable] FlyCross
    {COMMENTS}
    """


@schema
class RearingMethod(ManualLookup, dj.Manual):
    primary_comment = 'how the fly was raised - e.g. 25C, darkness'


@schema
class FlySubject(dj.Manual):
    definition = f"""
    subject_id : int auto_increment
    ---
    -> FlyGenotype
    -> Experimenter
    -> [nullable] RearingMethod
    sex = 'U' : enum('F', 'M', 'U')
    age = null : float # age of fly in days
    prep_time = CURRENT_TIMESTAMP : timestamp # time of prep
    {COMMENTS}
    """
