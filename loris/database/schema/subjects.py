"""Schema for Fish Subjects
"""

import datajoint as dj

from loris.database.schema.experimenters import Experimenter
from loris.database.schema.base import (
    ManualLookup, COMMENTS, PRIMARY_NAME, TAGS
)
from loris.database.attributes import chr, link, fishidentifier, crossschema
from loris.database.attributes import lookupname, tags


schema = dj.Schema('subjects')


@schema
class FishGenotype(dj.Manual):
    definition = f"""
    genotype_id : int auto_increment
    ---
    date_modified : date
    genotype_name : varchar(127)
    public_ids = null : <tags>
    {TAGS}
    {COMMENTS}
    """


@schema
class FishSubject(dj.Manual):
    definition = f"""
    subject_id : int auto_increment
    ---
    subject_name = null : varchar(255) # custom subject name -- not necessarily unique
    -> FishGenotype
    -> Experimenter
    dof = null : date # date of fertilization
    {TAGS}
    {COMMENTS}
    """
