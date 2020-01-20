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
class FlyCrosses(dj.Manual):
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
class FlyStock(dj.Manual):
    definition = f"""
    {PRIMARY_NAME.format(name='stock_name', comment='stock identification name')}
    ---
    date_modified : date
    -> FlyGenotype
    status = null : enum('dead', 'missing', 'instock', 'inpersonal', 'quarantine', 'recovery')
    -> [nullable] FlyOrigin
    -> [nullable] FlyCrosses
    {COMMENTS}
    """


@schema
class RearingMethod(ManualLookup, dj.Manual):
    pass


@schema
class FlySubject(dj.Manual):
    definition = f"""
    {PRIMARY_NAME.format(name='subject_name', comment='short subject name of fly')}
    ---
    -> FlyGenotype
    -> Experimenter
    -> [nullable] RearingMethod
    sex = 'U' : enum('F', 'M', 'U')
    age = null : float # age of fly in days
    prep_time = CURRENT_TIMESTAMP : timestamp # time of prep
    {COMMENTS}
    """
