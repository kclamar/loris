"""some core schema (mostly lookup schema)
"""

import datajoint as dj

from loris.database.schema.base import ManualLookup
from loris.database.attributes import lookupname


schema = dj.Schema('core')


@schema
class LookupName(ManualLookup, dj.Manual):
    primary_comment = 'identifiable name - e.g. stimulus, xml_file, array'


@schema
class ExtensionLookupName(ManualLookup, dj.Manual):
    primary_comment = 'identifiable name - e.g. prairieview, axograph'


@schema
class DataLookupName(ManualLookup, dj.Manual):
    primary_comment = 'identifiable name - e.g. stimulus, array, movie'


@schema
class FileLookupName(ManualLookup, dj.Manual):
    primary_comment = 'identifiable name - e.g. xml_file, settings'


@schema
class LookupRegex(ManualLookup, dj.Manual):
    primary_comment = 'a regular expression commonly used'
