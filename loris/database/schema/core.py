"""some core schema (mostly lookup schema)
"""

import datajoint as dj

from loris.database.schema.base import ManualLookup


schema = dj.schema('core')


@schema
class LookupName(ManualLookup, dj.Manual):
    primary_comment = 'identifiable name - e.g. stimulus, xml-file, array'


@schema
class LookupRegex(ManualLookup, dj.Manual):
    primary_comment = 'a regular expression commonly used'
