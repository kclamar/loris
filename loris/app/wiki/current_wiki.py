"""
"""

from flask import g
from werkzeug.local import LocalProxy

from loris import config
from loris.app.wiki.wiki import Wiki


def get_wiki():
    wiki = getattr(g, '_wiki', None)
    if wiki is None:
        wiki = g._wiki = Wiki(config['wiki_folder'])
    return wiki


current_wiki = LocalProxy(get_wiki)
