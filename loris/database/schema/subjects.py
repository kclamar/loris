"""Schema for Fly Subjects
"""

import datajoint as dj

from .experimenters import Experimenter
from .base import ManualLookup, COMMENTS, PRIMARY_NAME
from ..attributes import Chromosome, Link, FlyIdentifier, CrossSchema


schema = dj.schema('subjects')

# initialize custom attributes
chr = Chromosome()
link = Link()
flyidentifier = FlyIdentifier()
crossschema = CrossSchema()


@schema
class CellType(ManualLookup, dj.Manual):
    pass


@schema
class FlyOrigin(ManualLookup, dj.Manual):
    pass


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
        ---
        identifier : <flyidentifier> # public identifier
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
    {PRIMARY_NAME.format(name='stock_name')}
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
    {PRIMARY_NAME.format(name='subject_name')}
    ---
    -> FlyGenotype
    -> Experimenter
    -> [nullable] RearingMethod
    sex = 'U' : enum('F', 'M', 'U')
    age = null : float # age of fly in days
    prep_time = CURRENT_TIMESTAMP : timestamp # time of prep
    {COMMENTS}
    """
