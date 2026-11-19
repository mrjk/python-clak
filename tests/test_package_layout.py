"""Smoke tests: old deep import paths stay compatible after package reorg."""

from importlib.metadata import version

import pytest

import clak

pytestmark = pytest.mark.tags("unit-tests")


def test_version_matches_package_metadata():
    dist_version = version("mrjk.clak")
    assert clak.__version__ == dist_version
    assert dist_version
    assert dist_version != "0.0.0"


def test_compat_core_reexports():
    from clak import Parser as TopParser
    from clak.argparse_ import OPTIONAL, SUPPRESS
    from clak.core.parser import Parser as CoreParser
    from clak.descriptors import Argument, SubParser
    from clak.nodes import NOT_SET, Node
    from clak.parser import Argument as ParserArgument
    from clak.parser import Parser
    from clak.plugins import CLI_HOOK_PREFIX

    assert Parser is TopParser is CoreParser
    assert ParserArgument is Argument
    assert SubParser is not None
    assert NOT_SET is not None
    assert Node is not None
    assert CLI_HOOK_PREFIX == "cli_hook__"
    assert OPTIONAL is not None
    assert SUPPRESS is not None
    from clak.core.argp.parser import ArgumentParser as ArgpParser

    assert ArgpParser is not None


def test_compat_runtime_reexports():
    from clak.facts import detect_facts
    from clak.log_levels import register_clak_log_levels
    from clak.runtime import ClakSettings, detect_runtime
    from clak.runtime.facts import detect_facts as DetectFactsNew
    from clak.runtime.runtime import detect_runtime as DetectRuntimeNew
    from clak.settings import CLAK_DEBUG, resolve_log_colors

    assert detect_runtime is DetectRuntimeNew
    assert detect_facts is DetectFactsNew
    assert callable(resolve_log_colors)
    assert CLAK_DEBUG is not None
    assert callable(register_clak_log_levels)
    assert ClakSettings.from_env().colors in (True, False)


def test_compat_views_reexports():
    from clak.table_formatter import TableListFormatter, TableShowFormatter
    from clak.views import ListView, ShowView
    from clak.views.table_formatter import TableListFormatter as NewListFmt

    assert TableListFormatter is NewListFmt
    assert ShowView is not None
    assert ListView is not None
    assert TableShowFormatter is not None


def test_ui_package_is_portable():
    """clak.ui must stay copy-pasteable: no import of the rest of clak."""
    import ast
    from pathlib import Path

    ui_dir = Path(clak.__file__).parent / "ui"
    for path in ui_dir.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("clak"), path
                assert node.level >= 1 or node.module in {
                    "__future__", "typing", "dataclasses", "itertools", "os",
                    "sys", "threading", "time", "re", "collections.abc",
                }, (path, node.module)
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("clak") for a in node.names), path
