"""import all views
"""

from loris import config

# TODO import specific functions only and add __all__
from .main import *
if config['include_fly']:
    from .fly import *
from .analysis import *
from .database import *
from .erd import *
from .entries import *
from .wiki import *
from .autoscripts import *
