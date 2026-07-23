"""Clak Component Module

This module provides core component mixins for extending parser functionality:

- CompCmdRender: Base completion rendering class
- CompRenderCmdMixin: Adds command completion support to parsers
- CompRenderOptMixin: Adds option completion support to parsers
- XDGConfigMixin: Adds XDG Base Directory path CLI flags
- LoggingOptMixin: Adds structured logging configuration
- ShowViewMixin / ListViewMixin / PprintViewMixin: Auto CLI views + options

These components can be mixed into parser classes to add specific features.
The completion mixins enable rich command-line completion; config and logging
mixins provide XDG path flags and logging setup.
"""

from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin
from clak.comp.config import XDGConfigMixin
from clak.comp.logging import LoggingOptMixin
from clak.comp.views import ListViewMixin, PprintViewMixin, ShowViewMixin
