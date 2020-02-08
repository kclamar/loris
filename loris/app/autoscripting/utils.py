"""utils functions for autoscripting
"""

import numpy as np
import json
import pickle
import pandas as pd


def json_reader(value):
    """read json file fields
    """

    with open(value, 'r') as f:
        value = json.load(f)

    return value


def array_reader(value):
    """read array file fields
    """

    if value.endswith('npy'):
        value = np.load(value)
    elif value.endswith('csv'):
        value = pd.read_csv(value).values
    elif value.endswith('pkl'):
        with open(value, 'rb') as f:
            value = pickle.load(f)

    assert isinstance(value, np.ndarray)
    return value


def recarray_reader(value):
    """read recarray file fields
    """

    return frame_reader(value).to_records(False)


def frame_reader(value):
    """read pandas dataframes file fields
    """

    if value.endswith('csv'):
        value = pd.read_csv(value)
    elif value.endswith('pkl'):
        with open(value, 'rb') as f:
            value = pickle.load(f)
    elif value.endswith('json'):
        value = pd.DataFrame(json_reader(value))

    assert isinstance(value, pd.DataFrame)
    return value


def series_reader(value):
    """read pandas series file fields
    """

    return pd.Series(json_reader(value))


class ListReader:

    def __init__(self, func):

        self.func = func

    def __call__(self, value):

        if value is None:
            return 

        return [self.func(val) for val in value]


class TupleReader:

    def __init__(self, func):

        self.func = func

    def __call__(self, value):

        if value is None:
            return

        return (self.func(val) for val in value)


class DictReader:

    def __init__(self, func_dict):
        self.func_dict = func_dict

    def __call__(self, value):

        if value is None:
            return

        for key, func in self.func_dict.items():
            value[key] = func(value[key])

        return value


class EnumReader:

    def __init__(self, value, choices):

        self.value = value
        self.choices = choices

    def __call__(self, value):

        if value is None:
            return

        index = self.choices.index(value)
        return self.value[index]
