"""Base classes for tables
"""

COMMENTS = 'comments = null : varchar(4000)'
DESCRIPTION = 'description = null : varchar(4000)'
PRIMARY_NAME = '{name} : varchar(127)'


class ManualLookup:

    @property
    def definition(self):
        return f"""
        {PRIMARY_NAME.format(name=self.table_name)}
        ---
        {COMMENTS}
        """
