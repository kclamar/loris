"""Transformer class
"""

import re

import pandas as pd
import numpy as np

RESERVED_COLUMNS = {'func_result', 'max_depth', 'dropna', 'transformer'}


class Transformer:
    """class to transform wide dataframes pulled from datajoint

    Parameters
    ----------
    table : pandas.DataFrame
        A dataframe with columns defining datatypes and rows being different
        entries. All column and index names must be identifier string types.
        Individual cells in the dataframe may have arbitrary objects in them.
    datacols : list-like
        The columns in the dataframe that are considered "data"; i.e. for
        example columns where each cell is a numpy.array, e.g. a timestamp
        array. Defaults to None.
    indexcols : list-like
        The columns in the dataframe that are immutable types, e.g. strings or
        integers. Defaults to None.
    inplace : bool
        If possible do not copy dataframe. Defaults to False.
    **shared_axes : dict
        Specify if two or more "data columns" share axes. The keyword
        will correspond to what the column will be called in the long
        dataframe. Each argument is a dictionary where the keys
        correspond to the names of the "data columns", which share
        an axis, and the value correspond to the depth/axis is shared
        for each "data column".

    Attributes
    ----------
    table : pandas.DataFrame
        The dataframe passed during initialization

    Methods
    -------
    tolong
    applyfunc
    mapfunc
    drop
    """

    def __init__(
        self, table,
        datacols=None, indexcols=None,
        inplace=False,
        **shared_axes
    ):
        assert isinstance(table, pd.DataFrame), "table must be a pandas DataFrame."

        truth = RESERVED_COLUMNS & set(table.columns)
        assert not truth, (
            f'dataframe has columns that are reserved: {truth}.'
        )

        if datacols is None and indexcols is None:
            # indexcols already in index
            pass
        else:
            if indexcols is None:
                indexcols = list(set(table.columns) - set(datacols))
            elif datacols is None:
                datacols = list(set(table.columns) - set(indexcols))

            # no columns given that are not in dataframe
            truth = set(datacols) - set(table.columns)
            assert not truth, (
                f'datacols contains columns not in dataframe: {truth}.'
            )
            truth = set(indexcols) - set(table.columns)
            assert not truth, (
                f'indexcols contains columns not in dataframe: {truth}.'
            )
            # keep original index for uniqueness
            if not indexcols:
                pass
            elif inplace:
                table.set_index(indexcols, append=True, inplace=True)
            else:
                table = table.set_index(indexcols, append=True)

            # if only a few columns were selected
            if set(table.columns) - set(datacols):
                table = table[datacols]

        assert isinstance(table.index, pd.MultiIndex), (
            "table index must be multiindex"
        )
        truth = all(
            str(col).isidentifier() for col in table.columns
        ) + all(
            str(name).isidentifier() for name in table.index.names
        )
        assert truth, (
            "all index names and column names must be string identifiers."
        )
        truth = any(
            str(name).startswith(str(col))
            for name in table.index.names
            for col in table.columns
        )
        assert not truth, (
            "not any index names can startwith the same name as column names."
        )

        if inplace:
            self._table = table
        else:
            self._table = table.copy()

        # stringify everything
        self.table.rename(
            columns={col: str(col) for col in self.table.columns},
            inplace=True
        )
        self.table.index.set_names(
            [str(name) for name in self.table.index.names],
            inplace=True
        )

        # attributes assigned on the go
        self._shared_axes = shared_axes
        self._df = None

    @property
    def df(self):
        if self._df is None:
            self.tolong(set_df=True)
        return self._df

    @property
    def table(self):
        return self._table

    def tolong(
        self, *, transformer=iter, max_depth=3, dropna=True,
        set_df=False, **shared_axes
    ):
        """
        Transform the dataframe into a long format dataframe.

        Parameters
        ----------
        transformer : callable
            function called on each cell for each "data column" to create
            a new pandas.Series. If the "data columns" only contain array-like
            objects the default function <iter> is sufficient. If the
            "data columns" also contain other objects such as dictionaries,
            it may be necessary to provide a custom callable.
        max_depth : int
            Maximum depth of expanding each cell, before the algorithm stops
            for each "data column". If we set the max_depth to 3, for example,
            a "data column" consisting of 4-D numpy.arrays will result in a
            long dataframe where the "data column" cells contain
            1-D numpy.arrays. If the arrays were 3-D, it will result in a
            long dataframe with floats/ints in each cell. Defaults to 3.
        dropna : bool
            Drop rows in long dataframe where all "data columns" are NaN.
        set_df : bool
            Whether to set the df attribute to the resulting
            long dataframe.
        **shared_axes : dict
            Specify if two or more "data columns" share axes. The keyword
            will correspond to what the column will be called in the long
            dataframe. Each argument is a dictionary where the keys
            correspond to the names of the "data columns", which share
            an axis, and the value correspond to the depth/axis is shared
            for each "data column".
        """

        # update with default
        shared_axes = {**self._shared_axes, **shared_axes}

        truth = all(
            (
                # key must be unique
                all((re.match(f'{col}[_]?[1-9]*$', key) is None)
                    for col in self.table.columns)
                and key not in self.table.index.names
                # must be dictionary
                and isinstance(shared, dict)
                # keys must be in columns
                and not (set(shared) - set(self.table.columns))
            )
            for key, shared in shared_axes.items()
        )
        assert truth, (
            'shared axes arguments must be dictionaries '
            'with keys corresponding to columns and '
            'values corresponding to axes. '
            'The keyword will correspond to the new column name; '
            'it must be unique and not start the same way as any '
            'column in the dataframe.'
        )

        # iterate of each data column
        for m, (label, series) in enumerate(self.table.items()):
            # set first depth
            n = 0
            # if series already not object skip
            while series.dtype == object and max_depth > n:
                series = self._superstack_series(
                    series, label, transformer, dropna,
                    self._get_col_name(label, n, shared_axes)
                )
                n += 1

            # TODO check if most efficient solution
            # convert series to frame
            names = set(series.index.names)
            _df = series.reset_index()
            #
            if not m:
                df = _df
            else:
                on = list(names & set(df.columns))
                df = pd.merge(df, _df, on=on, how='outer')

        if set_df:
            self._df = df
            return
        else:
            return df

    @staticmethod
    def _get_col_name(label, n, shared_axes):
        # if it is a shared axes the column name is key
        # else it is "label_n"
        for key, shared in shared_axes.items():
            if shared.get(label, None) == n:
                return key
        return f"{label}_{n}"

    @staticmethod
    def _superstack_series(series, label, transformer, dropna, col_name):
        # apply series transformer (iter is default for sequences)
        # series.index is already assumed to be multi index
        # transform into dataframe
        # this should automatically infer types
        table = series.apply(
            lambda x: pd.Series(transformer(x)),
            convert_dtype=True
        )
        # give columns index a name
        table.columns.name = col_name
        # stack dataframe
        series = table.stack(dropna=dropna)
        series.name = label
        return series

    def __getitem__(self, key):
        # if it is a dataframe return new instance of transformer
        selected_table = self.table[key]

        if isinstance(selected_table, pd.DataFrame):
            # TODO shared axes
            return self.__class__(selected_table)
        else:
            return selected_table

    def cols_tolong(self, *cols, **kwargs):
        """Same as tolong but only applied to specific columns
        """
        return self[list(cols)].tolong(**kwargs)

    def expand_col(self, col, reset_index=True):
        """
        Expand a column that contains long dataframes and return
        a single long dataframe.
        """

        series = self[col]
        long_df = pd.concat(
            list(series), keys=series.index, names=series.index.names,
            sort=False
        )

        if reset_index:
            return long_df.reset_index()
        else:
            return long_df

    def mapfunc(self, func, col, new_col_name=None, **kwargs):
        """apply a function to a single column

        Parameters
        ----------
        func : callable
            Function to apply.
        column : str
            Name of column
        new_col_name : str
            Name of computed new column. If None, this will be set
            to the name of the column; i.e. the name of the column will be
            overwritter. Defaults to None.
        **kwargs : dict
            Keyword Arguments passed to the apply method of a pandas.Series,
            and thus to the function.
        """
        if new_col_name is None:
            new_col_name = col
        self.table[new_col_name] = self._select_frame(
            self.table, col
        ).apply(func, **kwargs)
        return self

    def applyfunc(self, func, new_col_name, *args, extra_kwargs={}, **kwargs):
        """apply a function across columns by mapping args and kwargs
        of func.

        Parameters
        ----------
        func : callable
            Function to apply.
        new_col_name : str
            Name of computed new col.
        *args : tuple
            Arguments passed to function. Each argument should be a column
            in the dataframe. This value is passed instead of the string.
        extra_kwargs : dict
            Keyword arguments passed to function
        **kwargs : dict
            Same as *args just as keyword arguments.
        """
        if new_col_name is None:
            new_col_name = 'func_result'
        self.table[new_col_name] = self.table.reset_index().apply(
            lambda x: func(
                *(x[arg] for arg in args),
                **{key: x[arg] for key, arg in kwargs.items()},
                **extra_kwargs
            ),
            axis=1, result_type='reduce'
        )
        return self

    @staticmethod
    def _select_frame(table, col):
        if col in table.columns:
            return table[col]
        else:
            table.index.to_frame(False)[col]

    def drop(self, *columns):
        """drop columns
        """
        self.table.drop(
            columns=columns,
            inplace=True
        )
        return self
