"""Parser engine: Parser, Argument, Command, context, argparse adapter."""

from clak.core.argp import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE
from clak.core.context import ClakContext, CliArgs
from clak.core.descriptors import Arg, Argument, MetaSetting, Opt, SubParser
from clak.core.parser import CLI_HOOK_PREFIX, Command, Parser, ParserNode

__all__ = [
    "CLI_HOOK_PREFIX",
    "CliArgs",
    "ClakContext",
    "ONE_OR_MORE",
    "OPTIONAL",
    "SUPPRESS",
    "ZERO_OR_MORE",
    "Arg",
    "Argument",
    "Command",
    "MetaSetting",
    "Opt",
    "Parser",
    "ParserNode",
    "SubParser",
]
