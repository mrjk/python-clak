"""Smoke tests: old deep import paths stay compatible after package reorg."""

import pytest

pytestmark = pytest.mark.tags("unit-tests")


def test_compat_core_reexports():
    from clak import Parser as TopParser
    from clak.argparse_ import OPTIONAL, SUPPRESS
    from clak.core.parser import Parser as CoreParser
    from clak.descriptors import Argument, SubParser
    from clak.nodes import NOT_SET, Node
    from clak.parser import Argument as ParserArgument
    from clak.parser import Parser
    from clak.plugins import PluginHelpers

    assert Parser is TopParser is CoreParser
    assert ParserArgument is Argument
    assert SubParser is not None
    assert NOT_SET is not None
    assert Node is not None
    assert PluginHelpers is not None
    assert OPTIONAL is not None
    assert SUPPRESS is not None


def test_compat_runtime_reexports():
    from clak.facts import detect_facts
    from clak.log_levels import register_clak_log_levels
    from clak.runtime import detect_runtime
    from clak.runtime.facts import detect_facts as DetectFactsNew
    from clak.runtime.runtime import detect_runtime as DetectRuntimeNew
    from clak.settings import CLAK_DEBUG, resolve_log_colors

    assert detect_runtime is DetectRuntimeNew
    assert detect_facts is DetectFactsNew
    assert callable(resolve_log_colors)
    assert CLAK_DEBUG is not None
    assert callable(register_clak_log_levels)


def test_compat_views_reexports():
    from clak.table_formatter import TableListFormatter, TableShowFormatter
    from clak.views import ListView, ShowView
    from clak.views.table_formatter import TableListFormatter as NewListFmt

    assert TableListFormatter is NewListFmt
    assert ShowView is not None
    assert ListView is not None
    assert TableShowFormatter is not None
