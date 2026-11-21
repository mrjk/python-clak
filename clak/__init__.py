"""Clak: A Command Line Application Kit.

Clak is a framework for building command line applications in Python. It extends
and enhances Python's argparse with features like:

- Simplified parser composition and inheritance
- Rich command completion support
- XDG Base Directory path flags and config-file loading (`XDGConfFileMixin`,
  `XDGDataDirMixin`, `XDGCacheDirMixin`, `XDGLogDirMixin`)
- Structured logging configuration
- Recursive subcommand handling

Canonical public API (import from ``clak``):
- Parser: root/command class (auto-dispatches on init unless parse=False)
- Argument: positional or optional argument descriptor
- Arg / Opt: optional sugar for positionals vs flags (Argument still accepts both)
- Command: nested subcommand descriptor (``SubParser`` is the class name)

Optional mixins (also from ``clak``): ApiServerMixin, ApiEndpointMixin, LoggingOptMixin, RuntimeOptMixin, RichHelpMixin,
Show/List/Pprint/Raw/Markdown/Rst/Data/CompositeViewMixin, completion,
XDGConfFileMixin / XDGDataDirMixin / XDGCacheDirMixin / XDGLogDirMixin,
WorkDirMixin.

Secondary entry points: ``clak.exception``, ``clak.views`` (view classes),
``clak.comp`` (mixins). Internal layout: ``clak.core``, ``clak.runtime``,
``clak.views``, ``clak.comp``.
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
from clak.comp.api import ApiEndpointMixin, ApiServeCmd, ApiServerMixin
from clak.comp.runtime import RuntimeOptMixin
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
from clak.core.argp import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE
from clak.core.descriptors import Arg, Argument, Opt, SubParser
from clak.core.help_render import RecursiveHelpFormatter
from clak.core.parser import Command, Parser, ParserNode


def __getattr__(name):
    """Resolve ``__version__`` lazily (importlib.metadata is slow to import)."""
    if name != "__version__":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # pylint: disable-next=import-outside-toplevel
    from importlib.metadata import PackageNotFoundError, version

    try:
        value = version("mrjk.clak")
    except PackageNotFoundError:
        value = "0.0.0"
    globals()["__version__"] = value
    return value


__all__ = [
    "__version__",  # pylint: disable=undefined-all-variable  (lazy, see __getattr__)
    "Arg",
    "Argument",
    "Command",
    "CompCmdRender",
    "CompRenderCmdMixin",
    "CompRenderOptMixin",
    "CompositeViewMixin",
    "DataViewMixin",
    "ListViewMixin",
    "LoggingOptMixin",
    "MarkdownViewMixin",
    "ONE_OR_MORE",
    "OPTIONAL",
    "Opt",
    "Parser",
    "ParserNode",
    "PprintViewMixin",
    "RawViewMixin",
    "RecursiveHelpFormatter",
    "RichHelpMixin",
    "RstViewMixin",
    "ApiEndpointMixin",
    "ApiServeCmd",
    "ApiServerMixin",
    "RuntimeOptMixin",
    "SUPPRESS",
    "ShowViewMixin",
    "SubParser",
    "WorkDirMixin",
    "XDGCacheDirMixin",
    "XDGConfFileMixin",
    "XDGDataDirMixin",
    "XDGLogDirMixin",
    "ZERO_OR_MORE",
]
