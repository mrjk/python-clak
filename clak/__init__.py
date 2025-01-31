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
from clak.parser import Parser  # , Opt, Arg, Cmd

# Parser = Parser
# Argument = Argument
# Opt = Opt - TODO
# Arg = Arg - TODO
Cmd = SubParser
