"""Login classes
"""

from flask_login import UserMixin
import datajoint as dj

from loris import config
from loris.settings import Config


class User(UserMixin):

    def __init__(self, user_name):
        self.table = config.user_table

        if not len(self.table()):
            config.create_administrator()

        self.user_name = user_name

        self.restriction = {config['user_name']: self.user_name}

        print(self.restriction)
        self.restricted_table = self.table & self.restriction

        if len(self.restricted_table) > 1:
            raise Exception('more than a single user entry')

        self._entry = None

    @property
    def entry(self):

        if self._entry is None:
            if config['user_active'] is None:
                self._entry = self.restricted_table.proj(
                    config['user_name'],
                ).fetch1()

            else:
                self._entry = self.restricted_table.proj(
                    config['user_name'],
                    config['user_active'],
                ).fetch1()

        return self._entry

    @property
    def user_exists(self):
        return len(self.restricted_table)

    def get_id(self):
        return str(self.user_name)

    @property
    def is_active(self):
        if config['user_active'] is None:
            return True
        return bool(self.entry[config['user_active']])

    @property
    def is_authenticated(self):
        return self.is_active

    def check_password(self, password):
        # check password in mysql database
        try:
            dj.conn(
                None, self.user_name, password,
                reset=True
            )
            success = True
        except Exception:
            success = False
        config.conn(reset=True)
        return success

    def get_user_config(self, password):
        """create user specific config file
        """

        user_config = Config.load()
        user_config['database.user'] = self.user_name
        user_config['database.password'] = password
        user_config.conn(reset=True)
        return user_config
