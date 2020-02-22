"""schema for experimenters
"""


import datajoint as dj

from loris.database.schema.base import COMMENTS, ManualLookup, PRIMARY_NAME
from loris.database.attributes import truebool
from loris.database.attributes import lookupname
from loris.database.attributes import email
from loris.database.attributes import phone


schema = dj.Schema('experimenters')


@schema
class Experimenter(dj.Manual):
    definition = f"""
    {PRIMARY_NAME.format(name='experimenter', comment='lowercase git user-name')}
    ---
    first_name : varchar(63)
    last_name : varchar(127)
    email : <email>
    phone : <phone>
    date_joined : date
    active = 0 : <truebool> # active member of the lab
    """

    class EmergencyContact(dj.Part):
        definition = f"""
        -> Experimenter
        contact_name : varchar(255)
        ---
        relation : varchar(63)
        phone : <phone>
        email = null : <email>
        {COMMENTS}
        """


@schema
class ExperimentalProject(ManualLookup, dj.Manual):
    primary_comment = 'name of experimental project'


@schema
class AssignedExperimentalProject(dj.Manual):
    definition = """
    -> Experimenter
    -> ExperimentalProject
    """
