"""Clak: A Command Line Application Kit.

Clak is a framework for building command line applications in Python. It extends
and enhances Python's argparse with features like:

- Simplified parser composition and inheritance
- Rich command completion support
- XDG config file integration
- Structured logging configuration
- Recursive subcommand handling

The framework provides both a classic API compatible with argparse and a modern,
more declarative API for defining commands.

Key components:
- Parser: Enhanced ArgumentParser with plugin support
- SubParser: For creating command hierarchies
- CompRenderCmdMixin: For command completion
- XDGConfigMixin: For config file handling
- LoggingOptMixin: For logging setup
"""


# Parsers imports
# Argparse public helpers
from clak.argparse import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE
from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin

# Plugins import
from clak.comp.config import XDGConfigMixin
from clak.comp.logging import LoggingOptMixin
from clak.parser import Argument, Parser, SubParser

# Classic API
ArgumentParser = Parser
# Argument = Argument
SubCommand = SubParser
Command = SubParser

# Modern API
# from clak.parser import Parser  # , Opt, Arg, Cmd

# Parser = Parser
# Argument = Argument
# Opt = Opt - TODO
# Arg = Arg - TODO
Cmd = SubParser

__version__ = "0.3.0a0"

