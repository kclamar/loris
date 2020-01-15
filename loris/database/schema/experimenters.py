"""schema for experimenters
"""


import datajoint as dj

from .base import COMMENTS

schema = dj.schema('experimenters')


@schema
class Experimenter(dj.Manual):
    definition = f"""
    experimenter : varchar(31) #short user-name
    ---
    experimenter_initials : char(3)
    first_name : varchar(63)
    last_name : varchar(127)
    email : varchar(255)
    phone : varchar(16)
    date_joined : date
    """

    class EmergencyContact(dj.Part):
        definition = f"""
        -> Experimenter
        contact_name : varchar(255)
        ---
        relation : varchar(63)
        phone : varchar(31)
        email = null : varchar(255)
        {COMMENTS}
        """
