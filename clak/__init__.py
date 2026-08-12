"""Clak: A Command Line Application Kit.

Clak is a framework for building command line applications in Python. It extends
and enhances Python's argparse with features like:

- Simplified parser composition and inheritance
- Rich command completion support
- XDG Base Directory path flags and config-file loading (`XDGConfigMixin`)
- Structured logging configuration
- Recursive subcommand handling

Canonical public API (import from ``clak``):
- Parser: root/command class (auto-dispatches on init unless parse=False)
- Argument: positional or optional argument descriptor
- Command: nested subcommand descriptor (alias of SubParser)

Optional mixins (also from ``clak``): LoggingOptMixin,
Show/List/Pprint/Raw/Markdown/Rst/CompositeViewMixin, completion,
XDGConfigMixin.

Secondary entry points: ``clak.exception``, ``clak.views`` (view classes),
``clak.comp`` (mixins). Internal layout: ``clak.core``, ``clak.runtime``,
``clak.views``, ``clak.comp``. Deep module paths remain import-compatible.
"""

from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin
from clak.comp.config import XDGConfigMixin
from clak.comp.logging import LoggingOptMixin
from clak.comp.views import (
    CompositeViewMixin,
    ListViewMixin,
    MarkdownViewMixin,
    PprintViewMixin,
    RawViewMixin,
    RstViewMixin,
    ShowViewMixin,
)
from clak.core.argparse_ import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE
from clak.core.parser import Argument, Command, Parser, ParserNode, SubParser

# Legacy / short aliases (prefer Command)
ArgumentParser = Parser
SubCommand = SubParser
Cmd = SubParser

__version__ = "0.5.0"
