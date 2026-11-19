"""Clak Component Module

This module provides core component mixins for extending parser functionality:

- CompCmdRender: Base completion rendering class
- CompRenderCmdMixin: Adds command completion support to parsers
- CompRenderOptMixin: Adds option completion support to parsers
- XDGConfFileMixin: Adds --conf-file (XDG default) and config-file loading
- XDGDataDirMixin / XDGCacheDirMixin / XDGLogDirMixin: Add one XDG path flag each
- WorkDirMixin: Adds -W/--work-dir (changes the process working directory)
- LoggingOptMixin: Adds structured logging configuration
- RuntimeOptMixin: Adds --interactive/--no-input/--yes runtime flags
- RichHelpMixin: Optional re-opt-in for Rich-colored --help after a parent opt-out
- Show/List/Pprint/Raw/Markdown/Rst/Data/CompositeViewMixin: Auto CLI views + options

These components can be mixed into parser classes to add specific features.
The completion mixins enable rich command-line completion; config and logging
mixins provide XDG paths, config loading, and logging setup.
"""

from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin
from clak.comp.config import (
    WorkDirMixin,
    XDGCacheDirMixin,
    XDGConfFileMixin,
    XDGDataDirMixin,
    XDGLogDirMixin,
)
from clak.comp.help import RichHelpMixin
from clak.comp.logging import LoggingOptMixin
from clak.comp.runtime import (
    RuntimeOptMixin,
    set_ui_settings,
    ui_policy,
    ui_session,
)
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
