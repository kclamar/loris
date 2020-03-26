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


def save_join(tables):
    """savely join tables ignoring dependent attributes that match.
    """

    for n, table in enumerate(tables):

        if n == 0:
            joined_table = table
        else:
            dep1 = joined_table.heading.secondary_attributes
            dep2 = table.heading.secondary_attributes
            proj = list(set(dep2) - set(dep1))
            joined_table = joined_table * table.proj(*proj)

    return joined_table
