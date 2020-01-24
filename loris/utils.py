"""Basic utility functions
"""


def is_manuallookup(table, ):
    """check if table is a manuallookup table
    """

    truth = False

    if (
        (len(table.heading.primary_key) == 1)
        and (len(table.heading.secondary_attributes) <= 1)
    ):
        pk = table.heading.primary_key[0]
        try:
            sk = table.heading.secondary_attributes[0]
        except IndexError:
            sk = 'comments'

        truth = (
            (sk == 'comments')
            & (pk == table.table_name)
        )

    return truth
