"""
"""

import graphviz
import os
import pandas as pd
import uuid
import glob
import datajoint as dj
from datajoint.schema import lookup_class_name
from flask import render_template, request, flash, url_for, redirect

from loris import config, conn
from loris.utils import is_manuallookup


def save_join(tables):
    """savely join tables ignoring dependent attributes
    """

    for n, table in enumerate(tables):

        if n == 0:
            joined_table = table
        else:
            dep1 = joined_table.heading.secondary_attributes
            dep2 = table.heading.secondary_attributes
            proj = list(set(dep2) - set(dep1))
            joined_table = joined_table * table.proj(*proj)

    return joined_table


def get_jsontable(
    data, primary_key, edit_url=None, delete_url=None,
    overwrite_url=None, name=None
):
    """get json table from dataframe
    """

    if len(data) == 0:
        data = pd.DataFrame(
            columns=['_id']+list(data.columns)
        )
    else:
        _id = pd.Series(
            data[primary_key].to_dict('records')
        )
        _id.name = '_id'
        data = pd.concat([_id, data], axis=1)

    jsontable = {}
    jsontable['delete_url'] = str(delete_url)
    jsontable['edit_url'] = str(edit_url)
    jsontable['overwrite_url'] = str(overwrite_url)
    jsontable['execute'] = 'True'
    jsontable['id'] = str(name)
    jsontable['head'] = list(data.columns)
    jsontable['data'] = data.values
    return jsontable


def draw_helper(obj=None, type='table', only_essentials=False):
    """
    helper for drawing erds
    """
    # Do not redo when image exists
    if obj is None:
        filename = 'eerrdd'
    elif type == 'table':
        filename = obj.full_table_name
    else:
        filename = obj

    filename = filename + str(only_essentials)

    filepath = os.path.join(config['tmp_folder'], filename)
    filepaths = glob.glob(filepath + '*' + '.svg')
    if len(filepaths) == 1:
        return os.path.split(filepaths[0])[-1]

    print(filename)
    # add random string (for rendering purposes on browsers)
    random_string = str(uuid.uuid4())
    filename += random_string
    filepath += random_string

    # rankdir TB?
    # setup of graphviz
    graph_attr = {'size': '12, 12', 'rankdir': 'LR', 'splines': 'ortho'}
    node_attr = {
        'style': 'filled', 'shape': 'note', 'align': 'left',
        'ranksep': '0.1', 'fontsize': '10', 'fontfamily': 'opensans',
        'height': '0.2', 'fontname': 'Sans-Serif'
    }

    dot = graphviz.Digraph(
        graph_attr=graph_attr, node_attr=node_attr,
        engine='dot', format='svg')

    def add_node(name, node_attr={}):
        """
        Add a node/table to the current graph (adding subgraphs if needed).
        """

        table_names = dict(
            zip(['schema', 'table', 'subtable'], name.split('.'))
        )
        graph_attr = {
            'color': 'grey80', 'style': 'filled',
            'label': table_names['schema']
        }

        with dot.subgraph(
            name='cluster_{}'.format(table_names['schema']),
            node_attr=node_attr,
            graph_attr=graph_attr
        ) as subgraph:
            subgraph.node(
                name, label=name.split('.')[-1],
                URL=url_for('table', **table_names),
                target='_top', **node_attr
            )
        return name

    def name_lookup(full_name):
        """ Look for a table's class name given its full name. """
        return lookup_class_name(full_name, config['schemata']) or full_name

    def is_essential(name):
        truth = dj.diagram._get_tier(name) in [
            dj.Manual, dj.Computed, dj.Lookup,
            dj.Imported, dj.AutoComputed, dj.AutoImported
        ]

        if truth:
            try:
                schema, table = name_lookup(name).split('.')
                table = getattr(
                    config['schemata'][schema],
                    table
                )
                truth = not is_manuallookup(table)
            except (KeyError, ValueError):
                print('did not check essential table')

        return truth

    node_attrs = {
        dj.Manual: {'fillcolor': 'green3'},
        dj.Computed: {'fillcolor': 'coral1'},
        dj.Lookup: {'fillcolor': 'azure3'},
        dj.Imported: {'fillcolor': 'cornflowerblue'},
        dj.Part: {'fillcolor': 'azure3', 'fontsize': '6'},
        dj.Settingstable: {'fillcolor': 'orange', 'fontsize': '6'},
        dj.AutoComputed: {'fillcolor': 'coral1'},
        dj.AutoImported: {'fillcolor': 'cornflowerblue'},
    }

    if type == 'table':
        root_table = obj
        root_dependencies = root_table.connection.dependencies
        root_dependencies.load()
        root_name = root_table.full_table_name
        root_id = add_node(
            name_lookup(root_name), node_attrs[dj.diagram._get_tier(root_name)]
        )

        # in edges
        for node_name, _ in root_dependencies.in_edges(root_name):
            if dj.diagram._get_tier(node_name) is dj.diagram._AliasNode:
                # renamed attribute
                node_name = list(root_dependencies.in_edges(node_name))[0][0]

            node_id = add_node(
                name_lookup(node_name),
                node_attrs[dj.diagram._get_tier(node_name)]
            )
            dot.edge(node_id, root_id)

        # out edges
        for _, node_name in root_dependencies.out_edges(root_name):
            if dj.diagram._get_tier(node_name) is dj.diagram._AliasNode:
                # renamed attribute
                node_name = list(root_dependencies.out_edges(node_name))[0][1]

            node_id = add_node(
                name_lookup(node_name),
                node_attrs[dj.diagram._get_tier(node_name)]
            )
            dot.edge(root_id, node_id)
    else:
        dependencies = config['connection'].dependencies
        dependencies.load()
        for root_name in dependencies.nodes.keys():
            try:
                int(root_name)
                continue
            except Exception:
                pass
            schema = root_name.replace('`', '').split('.')[0]
            if obj is None and schema in config['skip_schemas']:
                continue
            if obj is not None and (obj != schema):
                continue
            if only_essentials and not is_essential(root_name):
                continue

            root_id = add_node(
                name_lookup(root_name),
                node_attrs[dj.diagram._get_tier(root_name)]
            )

            for _, node_name in dependencies.out_edges(root_name):
                if dj.diagram._get_tier(node_name) is dj.diagram._AliasNode:
                    # renamed attribute
                    node_name = list(dependencies.out_edges(node_name))[0][1]
                if only_essentials and not is_essential(node_name):
                    continue

                node_id = add_node(
                    name_lookup(node_name),
                    node_attrs[dj.diagram._get_tier(node_name)]
                )
                dot.edge(root_id, node_id)

    if os.path.exists(filepath):
        os.remove(filepath)
    dot.render(filepath)

    return f'{filename}.svg'
