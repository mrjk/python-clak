"""
View classes for command line output formatting.

Classes:
    ClakView: Base view class for rendering command output
    ShowView / ListView: Table-oriented views
    PprintView / RawView / MarkdownView / RstView: Text views

Functions:
    pformat_truncated: Format data with width constraints
"""

from clak.views.base import (
    DEFAULT_WIDTH_MODE,
    DEFAULT_WRAP_MODE,
    OUTPUT_FORMATS,
    TEXT_FORMATS,
    WIDTH_MODES,
    WRAP_MODES,
    ClakView,
    merge_view_settings,
    pformat_truncated,
    resolve_view_width,
)
from clak.views.table import (
    FeatureFullViewer,
    ListView,
    ShowView,
    format_list_payload,
    format_show_payload,
    normalize_columns,
    normalize_sort_columns,
    parse_columns,
    parse_sort_columns,
)
from clak.views.text import (
    MarkdownView,
    PprintView,
    RawView,
    RstView,
    render_markdown_text,
    render_rst_text,
    require_docutils,
    require_rich,
)

__all__ = [
    "ClakView",
    "DEFAULT_WIDTH_MODE",
    "DEFAULT_WRAP_MODE",
    "FeatureFullViewer",
    "ListView",
    "MarkdownView",
    "OUTPUT_FORMATS",
    "PprintView",
    "RawView",
    "RstView",
    "ShowView",
    "TEXT_FORMATS",
    "WIDTH_MODES",
    "WRAP_MODES",
    "format_list_payload",
    "format_show_payload",
    "merge_view_settings",
    "normalize_columns",
    "normalize_sort_columns",
    "parse_columns",
    "parse_sort_columns",
    "pformat_truncated",
    "render_markdown_text",
    "render_rst_text",
    "require_docutils",
    "require_rich",
    "resolve_view_width",
]
