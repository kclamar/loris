"""Customized attributes
"""

import re
import os
import shutil

import numpy as np
import datajoint as dj


class TrueBool(dj.AttributeAdapter):

    attribute_type = 'bool'

    def put(self, obj):
        if obj is None or np.isnan(obj):
            return
        return bool(obj)

    def get(self, value):
        return bool(value)


class Chromosome(dj.AttributeAdapter):

    attribute_type = 'varchar(511)'

    def put(self, obj):
        """perform checks before putting
        """

        if obj is None:
            return

        assert isinstance(obj, str), (
            f"object is not of type string, "
            f"but {type(obj)} for chromosome attribute")

        return obj

    def get(self, value):
        return value


class Link(dj.AttributeAdapter):

    attribute_type = 'varchar(511)'

    @staticmethod
    def is_url(obj):

        regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )

        return re.match(regex, obj) is not None

    def put(self, obj):
        """perform checks before putting
        """

        if obj is None:
            return

        assert isinstance(obj, str), (
            f"object is not of type string, "
            f"but {type(obj)} for link attribute")

        if not self.is_url(obj):
            raise dj.DatajointError(
                f"string {obj} is not a url for attribute {self}"
            )

        return obj

    def get(self, value):
        return value


class FlyIdentifier(dj.AttributeAdapter):

    attribute_type = 'varchar(255)'

    def put(self, obj):
        """perform checks before putting
        """

        if obj is None:
            return

        assert isinstance(obj, str), (
            f"object is not of type string, "
            f"but {type(obj)} for fly identifier attribute")

        return obj

    def get(self, value):
        return value


class CrossSchema(dj.AttributeAdapter):

    attribute_type = 'attach@attachstore'

    def put(self, obj):
        """perform checks before putting
        """

        if obj is None:
            return

        return obj

    def get(self, value):
        return value


class TarFolder(dj.AttributeAdapter):

    attribute_type = 'attach@attachstore'

    def put(self, obj):
        """perform checks before putting and archive folder
        """

        if obj is None:
            return

        assert os.path.exists(obj), f'path {obj} does not exist.'

        return shutil.make_archive(obj, 'tar', obj)

    def get(self, value):
        """unpack zip file
        """
        unpacked_file = os.path.splitext(value)[0]
        shutil.unpack_archive(value, unpacked_file)
        return unpacked_file


chr = Chromosome()
link = Link()
flyidentifier = FlyIdentifier()
crossschema = CrossSchema()
truebool = TrueBool()
tarfolder = TarFolder()

custom_attributes_dict = {
    'chr': chr,
    'link': link,
    'flyidentifier': flyidentifier,
    'crossschema': crossschema,
    'truebool': truebool,
    'tarfolder': tarfolder
}
