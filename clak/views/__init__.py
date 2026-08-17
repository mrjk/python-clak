"""View classes for command line output formatting.

Public names are the view classes and a few format/width constants.
Helpers (`parse_columns`, `merge_view_settings`, `require_yaml`, ...) live in
the submodules (`clak.views.table`, `clak.views.base`, ...).
"""

from clak.views.base import (
    DEFAULT_FORMAT_SCOPE,
    DEFAULT_LINE_LENGTH,
    DEFAULT_WIDTH_MODE,
    DEFAULT_WRAP_MODE,
    FORMAT_SCOPES,
    OUTPUT_FORMATS,
    TEXT_FORMATS,
    WIDTH_MODES,
    WRAP_MODES,
    ClakView,
)
from clak.views.composite import CompositeView
from clak.views.data import DATA_FORMATS, DataView
from clak.views.table import ListView, ShowView, TableView
from clak.views.text import MarkdownView, PprintView, RawView, RstView

__all__ = [
    "ClakView",
    "CompositeView",
    "DATA_FORMATS",
    "DEFAULT_FORMAT_SCOPE",
    "DEFAULT_LINE_LENGTH",
    "DEFAULT_WIDTH_MODE",
    "DEFAULT_WRAP_MODE",
    "DataView",
    "FORMAT_SCOPES",
    "ListView",
    "MarkdownView",
    "OUTPUT_FORMATS",
    "PprintView",
    "RawView",
    "RstView",
    "ShowView",
    "TEXT_FORMATS",
    "TableView",
    "WIDTH_MODES",
    "WRAP_MODES",
]
