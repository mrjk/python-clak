"""Clak Component Module

This module provides core component mixins for extending parser functionality:

- CompCmdRender: Base completion rendering class
- CompRenderCmdMixin: Adds command completion support to parsers
- CompRenderOptMixin: Adds option completion support to parsers
- XDGConfigMixin: Adds XDG Base Directory path CLI flags and config-file loading
- LoggingOptMixin: Adds structured logging configuration
- RichHelpMixin: Optional re-opt-in for Rich-colored --help after a parent opt-out
- Show/List/Pprint/Raw/Markdown/Rst/Data/CompositeViewMixin: Auto CLI views + options

These components can be mixed into parser classes to add specific features.
The completion mixins enable rich command-line completion; config and logging
mixins provide XDG paths, config loading, and logging setup.
"""

from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin
from clak.comp.config import XDGConfigMixin
from clak.comp.help import RichHelpMixin
from clak.comp.logging import LoggingOptMixin
from clak.comp.views import (
    CompositeViewMixin,
    DataViewMixin,
    ListViewMixin,
    MarkdownViewMixin,
    PprintViewMixin,
    RawViewMixin,
    RstViewMixin,
    ShowViewMixin,
)
