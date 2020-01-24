"""functions to create users, delete users and grant privileges
"""

import datajoint as dj

from loris import config


def grantuser(
    username,
    connection='%',
    password='dr0s0phila',
    adduser=False
):
    """Add a user to the database. Requires admin/granting access.
    It also adds a user-specific schema
    """

    # establish connection
    conn = config['connection']

    # for safety flush all privileges
    conn.query("FLUSH PRIVILEGES;")

    #create user
    if adduser:
        conn.query(
            "CREATE USER %s@%s IDENTIFIED BY %s;",
            (username, connection, password)
        )

    # create user-specific schema
    schema = dj.schema(username)

    privileges = {
        '*.*' : "DELETE, SELECT, INSERT, UPDATE, REFERENCES",
        f'{username}.*' : "ALL PRIVILEGES"
    }

    for dbtable, privilege in privileges.items():
        privilege = (f"GRANT {privilege} ON {dbtable} to %s@%s;")
        conn.query(privilege, (username, connection))

    conn.query("FLUSH PRIVILEGES;")
