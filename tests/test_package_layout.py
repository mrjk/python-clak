"""Package layout: public surface, removed legacy paths, ui portability."""

import importlib
from importlib.metadata import version

import pytest

import clak

pytestmark = pytest.mark.tags("unit-tests")


def test_version_matches_package_metadata():
    dist_version = version("mrjk.clak")
    assert clak.__version__ == dist_version
    assert dist_version
    assert dist_version != "0.0.0"


@pytest.mark.parametrize(
    "module",
    [
        "clak.argparse_",
        "clak.descriptors",
        "clak.facts",
        "clak.log_levels",
        "clak.nodes",
        "clak.parser",
        "clak.plugins",
        "clak.settings",
        "clak.table_formatter",
        "clak.views.rich_style",
        "clak.core.argparse_",
    ],
)
def test_legacy_shim_modules_are_removed(module):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_legacy_aliases_are_removed():
    for name in ("ArgumentParser", "SubCommand", "Cmd"):
        assert not hasattr(clak, name)
    assert clak.Command is clak.SubParser


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
                    "__future__",
                    "typing",
                    "dataclasses",
                    "itertools",
                    "os",
                    "sys",
                    "threading",
                    "time",
                    "re",
                    "collections.abc",
                }, (path, node.module)
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("clak") for a in node.names), path
