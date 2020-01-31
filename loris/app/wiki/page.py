"""page class
"""

from collections import OrderedDict
from io import open
import os

from loris.app.wiki.processor import Processor


class Page(object):
    """page class
    """

    def __init__(self, path, url, new=False):
        self.path = path
        self.url = url
        self._meta = OrderedDict()
        if not new:
            self.load()
            self.render()

    def __repr__(self):
        return f"<Page: {self.url}@{self.path}>"

    def load(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def render(self):
        processor = Processor(self.content)
        self._html, self.body, self._meta = processor.process()

    def save(self, update=True):
        folder = os.path.dirname(self.path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(self.path, 'w', encoding='utf-8') as f:
            for key, value in self._meta.items():
                line = f'{key}: {value}\n'
                f.write(line)
            f.write('\n')
            f.write(self.body.replace('\r\n', '\n'))
        if update:
            self.load()
            self.render()

    @property
    def meta(self):
        return self._meta

    def __getitem__(self, name):
        return self._meta[name]

    def __setitem__(self, name, value):
        self._meta[name] = value

    @property
    def html(self):
        return self._html

    def __html__(self):
        return self.html

    @property
    def title(self):
        try:
            return self['title']
        except KeyError:
            return self.url

    @title.setter
    def title(self, value):
        self['title'] = value

    @property
    def tags(self):
        try:
            return self['tags']
        except KeyError:
            return ""

    @tags.setter
    def tags(self, value):
        self['tags'] = value
