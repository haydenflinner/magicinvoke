"""
An `invoke` extension that adds support for lots of goodies. See
magicinvoke.py for more doc.
"""

from ._version import __version_info__, __version__  # noqa
from invoke import *  # noqa
from .magicinvoke import (  # noqa
    cachepath,
    magictask,
    get_params_from_ctx,
    skippable,
    InputPath,
    Lazy,
    OutputPath,
)
from . import exceptions  # noqa

# Things that are handy for everyone to have
try:
    from pathlib import Path  # Py3
except:
    from pathlib2 import Path  # Py2

try:
    import colored_traceback.auto as __colored_traceback
except ImportError:
    __colored_traceback = None

from .vendor.dotmap import DotMap as dotdict

__all__ = [
    "magictask",
    "get_params_from_ctx",
    "skippable",
    "InputPath",
    "Lazy",
    "OutputPath",
    "dotdict",
    "__colored_traceback",
    "Path",
]
