"""Argparse adapter isolation and version flags."""

import argparse
import ast
from pathlib import Path

import pytest

from clak.core.argp import ArgparseCapabilities, ArgumentParser, format_argument_error

pytestmark = pytest.mark.tags("unit-tests")

_FORBIDDEN_PREFIXES = (
    "clak.core.parser",
    "clak.core.descriptors",
    "clak.comp",
    "clak.runtime",
)


def test_argp_sources_do_not_import_clak_cli():
    """argp may import stdlib argparse only, not ParserNode / Rich / settings."""
    root = Path(__file__).resolve().parents[1] / "clak" / "core" / "argp"
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not any(
                    name == prefix or name.startswith(prefix + ".")
                    for prefix in _FORBIDDEN_PREFIXES
                ), f"{path.name} imports {name}"


def test_capabilities_by_version():
    old = ArgparseCapabilities.detect((3, 10))
    assert old.has_color_kwarg is False
    assert old.error_always_raises is False
    assert old.intermixed_reenters is True
    assert old.choice_quotes_in_errors is True

    py312 = ArgparseCapabilities.detect((3, 12))
    assert py312.error_always_raises is True
    assert py312.intermixed_reenters is False
    assert py312.choice_quotes_in_errors is False

    py314 = ArgparseCapabilities.detect((3, 14))
    assert py314.has_color_kwarg is True


def test_invalid_choice_is_quoted():
    parser = ArgumentParser(exit_on_error=False)
    parser.add_argument("--color", choices=("red", "green"))
    with pytest.raises(argparse.ArgumentError) as err:
        parser.parse_args(["--color", "yellow"])
    message = str(err.value)
    assert "choose from 'red', 'green'" in message
    assert "Could not parse" not in message
    wrapped = format_argument_error(err.value)
    assert wrapped.startswith("Could not parse command line:")
    assert "'yellow'" in wrapped
