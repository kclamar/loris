"""class for configurations
"""

import json
import os
import shutil
import inspect
import multiprocessing as mp
from collections import defaultdict
import datajoint as dj
from datajoint.settings import default
from datajoint.utils import to_camel_case
from sshtunnel import SSHTunnelForwarder, HandlerSSHTunnelForwarderError

from loris.database.attributes import custom_attributes_dict
from loris.utils import is_manuallookup
from loris.errors import LorisError


# defaults for application
defaults = dict(
    textarea_startlength=512,
    # UPLOAD EXTENSIONS
    extensions=['csv', 'npy', 'json', 'pkl'],
    attach_extensions=(
        ['csv', 'npy', 'json', 'pkl'] + [
            'tiff', 'png', 'jpeg', 'mpg', 'hdf', 'hdf5', 'tar', 'zip',
            'txt', 'gif', 'svg', 'tif', 'bmp', 'doc', 'docx', 'rtf',
            'odf', 'ods', 'gnumeric', 'abw', 'xls', 'xlsx', 'ini',
            'plist', 'xml', 'yaml', 'yml', 'py', 'js', 'php', 'rb', 'sh',
            'tgz', 'txz', 'gz', 'bz2', 'jpe', 'jpg', 'pdf'
        ]
    ),
    # foreign key select field limit
    fk_dropdown_limit=200,
    user_schema="experimenters",
    user_table="Experimenter",
    user_name="experimenter",
    group_schema="experimenters",
    group_table="ExperimentalProject",
    group_name="experimental_project",
    assignedgroup_schema="experimenters",
    assignedgroup_table="AssignedExperimentalProject",
    max_cpu=None,
    init_database=False,
    include_fly=True
)
AUTOSCRIPT_CONFIG = 'config.json'
EXPANDUSER_FIELDS = (
    'tmp_folder',
    'wiki_folder',
    'autoscript_folder',
    'ssh_pkey'
)


class Config(dict):

    @classmethod
    def load(cls):
        """load configuration class and perform necessary checks
        """

        root_dir = os.path.split(os.path.split(__file__)[0])[0]
        config_file = os.path.join(root_dir, 'config.json')

        with open(config_file, 'r') as f:
            config = json.load(f)

        config = {**defaults, **config}
        config = cls(config)
        config['custom_attributes'] = custom_attributes_dict
        config['_empty'] = []  # list of files in tmp to delete on refresh
        config['_autopopulate'] = {}  # dictionary of subprocesses
        config.perform_checks()

        return config

    def connect_ssh(self):
        """ssh tunneling

        see: https://sshtunnel.readthedocs.io/en/latest/
        """

        if self.get('server', None) is not None:
            return self['server']

        elif self.get('ssh_address', None) is not None:
            # inti kwargs for init
            remote_bind_address = (
                self['database.host'], self['database.port']
            )
            kwargs = {
                'remote_bind_address': remote_bind_address,
                'local_bind_address': remote_bind_address
            }

            # get signature
            signature = inspect.signature(SSHTunnelForwarder)

            for key, param in signature.parameters.items():
                if param.name in self:
                    kwargs[param.name] = self[param.name]

            print('parameters for ssh tunneling:')
            print(kwargs)

            # initialize server
            server = SSHTunnelForwarder(**kwargs)
            self['server'] = server

            # start server
            try:
                server.start()
            except HandlerSSHTunnelForwarderError:
                server.restart()

            return self['server']

    def disconnect_ssh(self):
        """ssh tunneling
        """

        if self.get('server', None) is not None:
            self['server'].stop()
            self['server'] = None

    def __getitem__(self, k):

        try:
            return super().__getitem__(k)
        except KeyError as e:
            if k == 'tables':
                self.refresh_tables()
                return self[k]
            elif k == 'schemata':
                self.refresh_schema()
                return self[k]
            elif k == 'dynamicforms':
                self[k] = {}
                return self[k]
            elif k == 'automaker_tables':
                self.refresh_automaker_tables()
                return self[k]
            elif k == 'settings_tables':
                self.refresh_settings_tables()
                return self[k]
            elif k == 'connection':
                return self.conn(reset=True)
            elif k == 'server':
                return self.connect_ssh()

            raise e

    def conn(self, *args, **kwargs):
        """connect to database with hostname, username, and password.
        """
        self.datajoint_configuration()
        self.connect_ssh()
        self['connection'] = dj.conn(*args, **kwargs)
        return self['connection']

    def datajoint_configuration(self):
        # --- managing external file stores for database --- #
        if 'stores' not in dj.config:
            dj.config['stores'] = {}

        for filestore_name, filestore in self['filestores'].items():
            filestore = os.path.expanduser(filestore)
            if not os.path.exists(filestore):
                os.makedirs(filestore)

            dj.config['stores'].update({
                filestore_name: {
                    'protocol': 'file',
                    'location': filestore
                }
            })

        # set datajoint variable in datajoint config
        for key, ele in default.items():
            if key in self:
                dj.config[key] = self[key]
            else:
                self[key] = ele

    def perform_checks(self):
        """perform various checks (create directories if they don't exist)
        """

        for path in EXPANDUSER_FIELDS:
            if path in self:
                self[path] = os.path.expanduser(self[path])

        if not os.path.exists(self['tmp_folder']):
            os.makedirs(self['tmp_folder'])

        if not os.path.exists(self['autoscript_folder']):
            os.makedirs(self['autoscript_folder'])

        if self['max_cpu'] is None:
            self['max_cpu'] = mp.cpu_count()

    def refresh_schema(self):
        """refresh container of schemas
        """
        schemata = {}
        for schema in dj.list_schemas():
            if schema in self["skip_schemas"]:
                continue
            # TODO error messages
            schemata[schema] = dj.VirtualModule(
                schema, schema, connection=self['connection'],
                add_objects=custom_attributes_dict,
                create_tables=True
            )
            # make sure jobs table has been created
            schemata[schema].schema.jobs

        self['schemata'] = schemata

    def get_table(self, full_table_name):
        """get table from schemata
        """

        schema, table_name = full_table_name.replace('`', '').split('.')

        schema_module = self['schemata'].get(schema, None)

        if schema_module is None:
            raise LorisError(
                f'schema {schema} not in database; refresh database'
            )

        table_name = table_name.strip('_#')
        table_name_list = table_name.split('__')
        if len(table_name_list) == 1:
            table_name = to_camel_case(table_name)
            try:
                return getattr(schema_module, table_name)
            except AttributeError:
                raise LorisError(
                    f'table {table_name} not in schema {schema}; '
                    'refresh database'
                )
        else:
            assert len(table_name_list) == 2, \
                f'invalid table name {table_name}.'
            table_name = to_camel_case(table_name_list[0])
            part_table_name = to_camel_case(table_name_list[1])
            try:
                return getattr(
                    getattr(schema_module, table_name),
                    part_table_name
                )
            except AttributeError:
                raise LorisError(
                    f'table {table_name} not in schema {schema} '
                    f'or part table {part_table_name} not in table {table_name}'
                    '; refresh database'
                )

    def refresh_tables(self):
        """refresh container of tables
        """

        tables = {}

        for schema, module in self['schemata'].items():
            # skip mysql schema etc
            if schema in self["skip_schemas"]:
                continue
            for key, ele in module.__dict__.items():
                if key.split('.')[0] in self['schemata']:
                    continue
                if isinstance(ele, dj.user_tables.OrderedClass):
                    if is_manuallookup(ele) or issubclass(ele, dj.Settingstable):
                        continue
                    tables[f'{schema}.{key}'] = ele

                    # get part tables
                    for part_name, part_table in ele.__dict__.items():
                        if isinstance(part_table, dj.user_tables.OrderedClass):
                            if issubclass(part_table, dj.Part):
                                tables[f'{schema}.{key}.{part_name}'] = \
                                    part_table

        self['tables'] = tables

        return tables

    @property
    def user_table(self):
        """return the user table
        """

        return getattr(
            self['schemata'][self['user_schema']],
            self['user_table'])

    @property
    def users(self):
        """get a list of all users
        """
        users = list(
            self.user_table.proj(self['user_name']).fetch()[self['user_name']]
        )

        if not users:
            self.create_administrator()

        return users

    def create_administrator(self):
        # insert administrator if not users exist and create
        self.user_table.insert1(self['administrator_info'])

        # use standard password
        password = self['standard_password']
        # establish connection
        conn = self['connection']
        connection = '%'
        username = self['administrator_info'][self['user_name']]

        # for safety flush all privileges
        conn.query("FLUSH PRIVILEGES;")

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
            '*.*': "ALL PRIVILEGES",
        }

        for dbtable, privilege in privileges.items():
            privilege = (f"GRANT {privilege} ON {dbtable} to %s@%s;")
            conn.query(privilege, (username, connection))

        conn.query("FLUSH PRIVILEGES;")

        return schema

    @property
    def user_tables(self):
        """return a list of user tables
        """
        return list(set(self.users) & set(self['schemata']))

    @property
    def group_table(self):
        """return the group table
        """

        return getattr(
            self['schemata'][self['group_schema']],
            self['group_table'])

    @property
    def groups(self):
        """get a list of all groups
        """
        groups = list(
            self.group_table.proj(
                self['group_name']
            ).fetch()[self['group_name']]
        )

        return groups

    @property
    def group_tables(self):
        """return a list of group tables
        """
        return list(set(self.groups) & set(self['schemata']))

    def create_group_schemas(self):
        """create all missing schemas
        """

        for group in self.groups:
            dj.Schema(group, connection=self['connection'])

    @property
    def assigned_table(self):
        """assigned table (matching groups and users)
        """

        return getattr(
            self['schemata'][self['assignedgroup_schema']],
            self['assignedgroup_table'])

    def groups_of_user(self, user):
        """groups user belongs to (includes user name)
        """

        groups = [user]

        table = self.assigned_table & {
            self['user_name'] : user
        }
        groups.extend(
            list(table.proj(self['group_name']).fetch()[self['group_name']])
        )

        return groups

    def schemas_of_user(self, user):
        """schemas user belongs to (should be the same as groups_of_user except
        when administrator), if each group has an associated schema.
        """

        if user in self['administrators']:
            return list(self['schemata'])

        groups = self.groups_of_user(user)
        return list(set(groups) & set(self['schemata']))

    def user_in_group(self, user, group):
        """is user in group
        """

        table = self.assigned_table & {
            self['user_name'] : user,
            self['group_name'] : group
        }

        if len(table) == 1:
            return True
        elif len(table) == 0:
            return False
        else:
            raise LorisError(
                "assined user group table should only have "
                "singular entries for given user and group."
            )

    def refresh_permissions(self):
        """refresh permissions of users
        """

        for user in self.users:
            for schema in self.schemas_of_user(user):
                conn = self['connection']
                conn.query("FLUSH PRIVILEGES;")
                conn.query(
                    f"GRANT ALL PRIVILEGES ON {schema}.* to %s@%s;",
                    (user, '%')
                )
                conn.query("FLUSH PRIVILEGES;")

    def refresh_settings_tables(self):
        """refresh container of settings table
        """

        tables = {}

        for table_name, table in self['tables'].items():
            if issubclass(table, dj.Settingstable):
                tables[table_name] = table

        self['settings_tables'] = tables

        return tables

    def refresh_automaker_tables(self):
        """refresh container of settings table
        """

        tables = {}

        for table_name, table in self['tables'].items():
            if issubclass(table, (dj.AutoImported, dj.AutoComputed)):
                tables[table_name] = table

        self['automaker_tables'] = tables

        return tables

    def tables_to_list(self):
        """convert tables container to list for app header
        """

        tables = self['tables']
        manualtables_dict = defaultdict(list)
        autotables_list = []

        for table_name, table in tables.items():
            if issubclass(table, dj.Manual):
                auto_class = False
                # ignore ManualLookup subclasses
                if (
                    is_manuallookup(table)
                    or (table.full_table_name
                        == self.user_table.full_table_name)
                    or (table.full_table_name
                        == self.group_table.full_table_name)
                    or (table.full_table_name
                        == self.assigned_table.full_table_name)
                ):
                    continue
            elif issubclass(table, (dj.AutoImported, dj.AutoComputed)):
                auto_class = True
            else:
                continue

            table_list = [table_name] + table_name.split('.') + [None]

            if auto_class:
                autotables_list.append(table_list)
            else:
                manualtables_dict[table_list[1]].append(table_list[2])

        return manualtables_dict, autotables_list

    def refresh_dependencies(self):
        """refresh dependencies of database connection
        """

        self['connection'].dependencies.load()

    def empty_tmp_folder(self):
        """empty temporary folder
        """

        for filename in os.listdir(self['tmp_folder']):
            if not any([filename.startswith(ele) for ele in self['_empty']]):
                continue
            file_path = os.path.join(self['tmp_folder'], filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

        self['_empty'] = []

    def refresh(self):
        """refresh all containers and empty temporary folder
        """

        self.pop('dynamicforms', None)
        self.pop('autoscriptforms', None)
        self.empty_tmp_folder()
        self.refresh_dependencies()
        self.refresh_schema()
        self.refresh_tables()
        self.refresh_settings_tables()
        self.refresh_automaker_tables()
        self.refresh_permissions()

    def get_dynamicform(
        self, table_name, table_class, dynamic_class, **kwargs
    ):
        """get the dynamic form and wtf form for application
        """

        name = dynamic_class.__name__

        if name not in self['dynamicforms']:
            self['dynamicforms'][name] = {}

        if table_name not in self['dynamicforms'][name]:
            dynamicform = dynamic_class(table_class)
            form = dynamicform.formclass(**kwargs)
            self['dynamicforms'][name][table_name] = dynamicform
        else:
            # update foreign keys
            dynamicform = self['dynamicforms'][name][table_name]
            form = dynamicform.formclass(**kwargs)
            dynamicform.update_fields(form)

        return dynamicform, form

    def get_autoscriptforms(
        self, autoscript_filepath, table_name, form_creator, **kwargs
    ):

        if 'autoscriptforms' not in self:
            self['autoscriptforms'] = {}
        if table_name not in self['autoscriptforms']:
            self['autoscriptforms'][table_name] = {}

        if autoscript_filepath in self['autoscriptforms'][table_name]:
            pass
        else:
            filepath = os.path.join(
                autoscript_filepath, AUTOSCRIPT_CONFIG
            )
            with open(filepath, 'r') as f:
                config = json.load(f)

            include_insert = not bool(config['autoscript_inserts'])
            buttons = config['scripts']

            if not isinstance(buttons, dict):
                raise LorisError(
                    f'In configuration file of autoscript '
                    f'"{os.path.basename(autoscript_filepath)}", '
                    '"scripts" keyword is incorrectly '
                    'formatted.'
                )

            for key, button in buttons.items():
                message = (
                    f'In configuration file of autoscript '
                    f'"{os.path.basename(autoscript_filepath)}", '
                    '"scripts" keyword is incorrectly '
                    f'formatted for button "{key}".'
                )
                if len(button) < 3 or len(button) > 4:
                    raise LorisError(message)
                elif len(button) == 4 and not isinstance(button[-1], dict):
                    raise LorisError(message)
                elif not all([
                    isinstance(button[0], str),
                    isinstance(button[1], list),
                    isinstance(button[2], bool)
                ]):
                    raise LorisError(message)

            if not isinstance(config['forms'], dict):
                raise LorisError(
                    f'In configuration file of autoscript '
                    f'"{os.path.basename(autoscript_filepath)}", '
                    '"forms" keyword is incorrectly '
                    'formatted.'
                )

            forms = {}
            post_process_dict = {}
            for key, value in config['forms'].items():
                form, post_process = form_creator(value, **kwargs)
                forms[key] = form
                post_process_dict[key] = post_process

            self['autoscriptforms'][table_name][autoscript_filepath] = (
                forms, post_process_dict, buttons, include_insert
            )

        return self['autoscriptforms'][table_name][autoscript_filepath]
