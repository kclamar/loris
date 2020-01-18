"""class for configurations
"""

import json
import os
import shutil
import datajoint as dj

from loris.database.attributes import custom_attributes_dict


class Config(dict):

    @classmethod
    def load(cls):

        root_dir = os.path.split(os.path.split(__file__)[0])[0]
        config_file = os.path.join(root_dir, 'config.json')

        with open(config_file, 'r') as f:
            config = json.load(f)

        return cls(config)

    def __getitem__(self, k):
        """
        """

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

        dj.config['database.host'] = self['database.host']
        dj.config['database.user'] = self['database.user']
        dj.config['database.password'] = self['database.password']
        dj.config['enable_python_native_blobs'] = \
            self['enable_python_native_blobs']
        dj.config['enable_python_pickle_blobs'] = \
            self['enable_python_pickle_blobs']
        dj.config['enable_automakers'] = self['enable_automakers']

    def perform_checks(self):
        """perform various checks
        """

        if not os.path.exists(self['tmp_folder']):
            os.makedirs(self['tmp_folder'])

    def refresh_schema(self):
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

                    for part_name, part_table in ele.__dict__.items():
                        if isinstance(part_table, dj.user_tables.OrderedClass):
                            tables[f'{schema}.{key}.{part_name}'] = part_table

        self['tables'] = tables

        return tables

    def refresh_dependencies(self):
        self['connection'].dependencies.load()

    def empty_tmp_folder(self):

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
        self.pop('dynamicforms', None)
        self.empty_tmp_folder()
        self.refresh_dependencies()
        self.refresh_schema()
        self.refresh_tables()

    def get_dynamicform(self, table_name, table_class, dynamic_class):

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

    # get all settings tables
    # get all automaker tables
