"""import virtual schema
"""

import datajoint as dj
from loris.database.attributes import custom_attributes_dict

schemata = {}

for schema in dj.list_schemas():
    schemata[schema] = dj.create_virtual_module(
        schema, schema, connection=dj.conn(),
        add_objects=custom_attributes_dict
    )
