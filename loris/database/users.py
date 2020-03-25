"""functions to create users, delete users and grant privileges
"""

import datajoint as dj

from loris import config


def change_password(username, password, connection='%'):
    """Change the password for a user. Requires administration access or
    being the user.
    """
    # establish connection
    conn = config['connection']
    # make sure all privileges have been flushed
    conn.query("FLUSH PRIVILEGES;")
    # change password
    conn.query("SET PASSWORD FOR %s@%s = %s;", (username, connection, password))
    #
    conn.query("FLUSH PRIVILEGES;")


def dropuser(username, connection='%'):
    """Drop a user from the database. Requires administration access.
    """
    # establish connection
    conn = config['connection']
    # flush privileges
    conn.query("FLUSH PRIVILEGES;")
    # drop user
    conn.query("DROP USER %s@%s;", (username, connection))
    #
    conn.query("FLUSH PRIVILEGES;")


def grantuser(
    username,
    connection='%',
    password=None,
    adduser=False
):
    """Add a user to the database. Requires admin/granting access.
    It also adds a user-specific schema
    """

    if password is None:
        password = config['standard_password']

    # establish connection
    conn = config['connection']

    # for safety flush all privileges
    conn.query("FLUSH PRIVILEGES;")

    #create user
    if adduser:
        conn.query(
            "DROP USER IF EXISTS %s@%s;",
            (username, connection)
        )
        conn.query(
            "CREATE USER %s@%s IDENTIFIED BY %s;",
            (username, connection, password)
        )

    # create user-specific schema
    schema = dj.Schema(username)

    privileges = {
        '*.*': "DELETE, SELECT, INSERT, UPDATE, REFERENCES, CREATE",
        f'{username}.*': "ALL PRIVILEGES"
    }

    grantprivileges(username, conn, privileges, connection)

    return schema


def grantprivileges(
    username,
    conn,
    privileges,
    connection='%',
):
    """grant privileges to user
    """

    conn.query("FLUSH PRIVILEGES;")

    for dbtable, privilege in privileges.items():
        privilege = (f"GRANT {privilege} ON {dbtable} to %s@%s;")
        conn.query(privilege, (username, connection))

    conn.query("FLUSH PRIVILEGES;")
