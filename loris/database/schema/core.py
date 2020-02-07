"""some core schema (mostly lookup schema)
"""

import datajoint as dj

from loris.database.schema.base import ManualLookup


schema = dj.schema('core')


@schema
class DataType(ManualLookup, dj.Manual):
    primary_comment = 'type of data - e.g. numpy.array, pandas.DataFrame, csv'


@schema
class RegexType(ManualLookup, dj.Manual):
    primary_comment = 'type of regular expression'
