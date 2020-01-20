"""class for configurations
"""

import json
import os
import shutil
import datajoint as dj
from datajoint.settings import default

from loris.database.attributes import custom_attributes_dict

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
    fk_dropdown_limit=200
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
        config.perform_checks()

        return config

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
                return self.conn()

            raise e

    def conn(self, *args, **kwargs):
        """connect to database with hostname, username, and password.
        """
        self.datajoint_configuration()
        self['connection'] = dj.conn(*args, **kwargs)
        return self['connection']

    def datajoint_configuration(self):
        # --- managing external file stores for database --- #
        if 'stores' not in dj.config:
            dj.config['stores'] = {}

        for filestore_name, filestore in self['filestores'].items():
            if not os.path.exists(filestore):
                os.makedirs(filestore)

            dj.config['stores'].update({
                filestore_name: {
                    'protocol': 'file',
                    'location': filestore
                }
            })

        # set datajoint variable in datajoint config
        for key in default:
            if key in self:
                dj.config[key] = self[key]

    def perform_checks(self):
        """perform various checks
        """

        if not os.path.exists(self['tmp_folder']):
            os.makedirs(self['tmp_folder'])

    def refresh_schema(self):
        """refresh container of schemas
        """
        schemata = {}
        for schema in dj.list_schemas():
            if schema in self["skip_schemas"]:
                continue
            schemata[schema] = dj.create_virtual_module(
                schema, schema, connection=self.conn(),
                add_objects=custom_attributes_dict
            )

        self['schemata'] = schemata

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
                    tables[f'{schema}.{key}'] = ele

                    # get part tables
                    for part_name, part_table in ele.__dict__.items():
                        if isinstance(part_table, dj.user_tables.OrderedClass):
                            if issubclass(part_table, dj.Part):
                                tables[f'{schema}.{key}.{part_name}'] = \
                                    part_table

        self['tables'] = tables

        return tables

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
        tables_list = []

        for table_name, table in tables.items():
            if issubclass(table, dj.Manual):
                # ignore ManualLookup subclasses
                if (
                    (len(table.heading.primary_key) == 1)
                    and (len(table.heading.secondary_attributes) == 1)
                ):
                    pk = table.heading.primary_key[0]
                    sk = table.heading.secondary_attributes[0]
                    truth = (
                        (sk == 'comments')
                        & (pk == table.table_name)
                    )
                    if truth:
                        continue
            else:
                continue

            tables_list.append(
                [table_name] + table_name.split('.')
            )
            if len(tables_list[-1]) == 3:
                tables_list[-1].append(None)

        return tables_list

    def refresh_dependencies(self):
        """refresh dependencies of database connection
        """

        self['connection'].dependencies.load()

    def empty_tmp_folder(self):
        """empty temporary folder
        """

        for filename in os.listdir(self['tmp_folder']):
            file_path = os.path.join(self['tmp_folder'], filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    def refresh(self):
        """refresh all containers and empty temporary folder
        """

        self.pop('dynamicforms', None)
        self.empty_tmp_folder()
        self.refresh_dependencies()
        self.refresh_schema()
        self.refresh_tables()
        self.refresh_settings_tables()
        self.refresh_automaker_tables()

    def get_dynamicform(self, table_name, table_class, dynamic_class):
        """get the dynamic form and wtf form for application
        """

        if table_name not in self['dynamicforms']:
            dynamicform = dynamic_class(table_class)
            form = dynamicform.formclass()
            self['dynamicforms'][table_name] = dynamicform
        else:
            # update foreign keys
            dynamicform = self['dynamicforms'][table_name]
            form = dynamicform.formclass()
            dynamicform.update_foreign_fields(form)

        return dynamicform, form
