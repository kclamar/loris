"""Base Class to handle fetched joined tables
"""

from abc import abstractmethod, ABC
import datajoint as dj

from loris import config
from loris.dataframe.transformer import Transformer


class Fetcher(ABC, Transformer):

    def __ini__(
        self,
        *projs,
        **renamed_projs
    ):
        pass

    def join(self):
        pass

    def fetch(self):
        pass

    @abstractmethod
    def tables_dict(self):
        pass

    def plot_grid(self):
        pass
