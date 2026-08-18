"""Isolated stdlib argparse adapter.

This package may import stdlib argparse and logging only. It must not import
ParserNode, descriptors, clak.comp, ClakSettings, or Rich.
"""

import argparse

from clak.core.argp.capabilities import ArgparseCapabilities
from clak.core.argp.errors import ErrorRenderer, format_argument_error
from clak.core.argp.parser import ArgumentParser, ArgumentParserPlus

ONE_OR_MORE = argparse.ONE_OR_MORE
OPTIONAL = argparse.OPTIONAL
PARSER = argparse.PARSER
REMAINDER = argparse.REMAINDER
SUPPRESS = argparse.SUPPRESS
ZERO_OR_MORE = argparse.ZERO_OR_MORE
ArgumentError = argparse.ArgumentError

__all__ = [
    "ArgumentError",
    "ArgumentParser",
    "ArgumentParserPlus",
    "ArgparseCapabilities",
    "ErrorRenderer",
    "ONE_OR_MORE",
    "OPTIONAL",
    "PARSER",
    "REMAINDER",
    "SUPPRESS",
    "ZERO_OR_MORE",
    "argparse",
    "format_argument_error",
]
