"""Clak Component Module

This module provides core component mixins for extending parser functionality:

- CompCmdRender: Base completion rendering class
- CompRenderCmdMixin: Adds command completion support to parsers
- CompRenderOptMixin: Adds option completion support to parsers
- XDGConfigMixin: Adds XDG config file handling capabilities
- LoggingOptMixin: Adds structured logging configuration

These components can be mixed into parser classes to add specific features.
The completion mixins enable rich command-line completion, while the config
and logging mixins provide configuration management and logging setup.
"""

from clak.comp.completion import CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin
from clak.comp.config import XDGConfigMixin
from clak.comp.logging import LoggingOptMixin
