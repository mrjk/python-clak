"""Clak: A Command Line Application Kit.

Clak is a framework for building command line applications in Python. It extends
and enhances Python's argparse with features like:

- Simplified parser composition and inheritance
- Rich command completion support
- XDG Base Directory path flags and config-file loading (`XDGConfigMixin`)
- Structured logging configuration
- Recursive subcommand handling

Canonical public API:
- Parser: root/command class (auto-dispatches on init unless parse=False)
- Argument: positional or optional argument descriptor
- Command: nested subcommand descriptor (alias of SubParser)

Optional mixins: LoggingOptMixin, Show/List/PprintViewMixin, completion, XDGConfigMixin.
"""

from clak.argparse_ import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE
from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin
from clak.comp.config import XDGConfigMixin
from clak.comp.logging import LoggingOptMixin
from clak.comp.views import ListViewMixin, PprintViewMixin, ShowViewMixin
from clak.parser import Argument, Command, Parser, ParserNode, SubParser

# Legacy / short aliases (prefer Command)
ArgumentParser = Parser
SubCommand = SubParser
Cmd = SubParser

__version__ = "0.4.0"
