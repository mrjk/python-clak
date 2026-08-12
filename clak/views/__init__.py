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
    merge_view_settings,
    normalize_width_mode,
    parse_line_length,
    pformat_truncated,
    resolve_line_length,
    resolve_view_width,
)
from clak.views.composite import CompositeView, normalize_sections
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
    "CompositeView",
    "DEFAULT_FORMAT_SCOPE",
    "DEFAULT_LINE_LENGTH",
    "DEFAULT_WIDTH_MODE",
    "DEFAULT_WRAP_MODE",
    "FORMAT_SCOPES",
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
    "normalize_sections",
    "normalize_sort_columns",
    "normalize_width_mode",
    "parse_columns",
    "parse_line_length",
    "parse_sort_columns",
    "pformat_truncated",
    "render_markdown_text",
    "render_rst_text",
    "require_docutils",
    "require_rich",
    "resolve_line_length",
    "resolve_view_width",
]
