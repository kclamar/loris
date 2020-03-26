"""utility functions for database
"""

import os

import loris


class Placeholder:
    """a file placeholder class for the placeholder custom attribute
    """

    filename = "placeholder.txt"

    def __init__(self, value):
        self.value = value

    @classmethod
    def read(cls, filepath):
        """read value
        """
        filename = os.path.split(filepath)[-1]
        if filename == cls.filename:
            with open(filepath, 'rb') as f:
                obj = f.read()
            return cls(obj)

        return filepath

    def write(self):
        """write value
        """
        if not os.path.exists(self.value):

            filepath = os.path.join(loris.config['tmp_folder'], self.filename)
            with open(filepath, 'wb') as f:
                f.write(self.value)
            return filepath

        return self.value


class ProcessMixin:
    """a mixin to process strings or other objects for
    blob serialization or attaching.
    """

    def put_process(obj):
        if obj is None:
            return
        return obj

    def get_process(value):

        return value
