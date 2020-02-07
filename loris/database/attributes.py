"""Customized attributes
"""

import re
import os
import shutil
import json

import numpy as np
import datajoint as dj

from loris.database.utils import Placeholder, ProcessMixin


class TrueBool(dj.AttributeAdapter):

    attribute_type = 'bool'

    def put(self, obj):
        if obj is None or np.isnan(obj):
            return
        return bool(obj)

    def get(self, value):
        return bool(value)


class ListString(dj.AttributeAdapter):

    attribute_type = 'varchar(4000)'

    def put(self, obj):
        if obj is None:
            return
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except Exception:
                pass
        assert isinstance(obj, (list, tuple)), \
            f'object must be list or tuple for liststring type: {type(obj)}'
        return json.dumps(obj)

    def get(self, value):
        return json.loads(value)


class DictString(dj.AttributeAdapter):

    attribute_type = 'varchar(4000)'

    def put(self, obj):
        if obj is None:
            return
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except Exception:
                pass
        assert isinstance(obj, (dict)), \
            f'object must be dict for dictstring type: {type(obj)}'
        return json.dumps(obj)

    def get(self, value):
        return json.loads(value)


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


class AttachProcess(dj.AttributeAdapter, ProcessMixin):

    attribute_type = 'attach@attachstore'

    def put(self, obj):
        return self.put_process(obj)

    def get(self, value):
        return self.get_process(value)


class AttachPlaceholder(dj.AttributeAdapter, ProcessMixin):

    attribute_type = 'attach@attachstore'

    def put(self, obj):
        """perform checks before putting and archive folder
        """

        if obj is None:
            return

        obj = self.put_process(obj)
        return Placeholder(obj).write()

    def get(self, value):
        """get file
        """
        return self.get_process(Placeholder.read(value))


chr = Chromosome()
link = Link()
flyidentifier = FlyIdentifier()
crossschema = CrossSchema()
truebool = TrueBool()
tarfolder = TarFolder()
liststring = ListString()
tags = ListString()
dictstring = DictString()
attachprocess = AttachProcess()
attachplaceholder = AttachPlaceholder()

custom_attributes_dict = {
    'chr': chr,
    'link': link,
    'flyidentifier': flyidentifier,
    'crossschema': crossschema,
    'truebool': truebool,
    'tarfolder': tarfolder,
    'liststring': liststring,
    'dictstring': dictstring,
    'tags': tags, 
    'attachprocess': attachprocess,
    'attachplaceholder': attachplaceholder
}
