
# Parsers imports
from clak.parser import Parser, Argument, SubParser

# Plugins import
from clak.comp.config import XDGConfigMixin
from clak.comp.logging import LoggingOptMixin
from clak.comp.completion import CompRenderOptMixin, CompRenderCmdMixin, CompCmdRender

# Classic API
ArgumentParser = Parser
# Argument = Argument
SubCommand = SubParser
Command = SubParser

# Modern API
from clak.parser import Parser #, Opt, Arg, Cmd
# Parser = Parser
# Argument = Argument
# Opt = Opt - TODO
# Arg = Arg - TODO
Cmd = SubParser

