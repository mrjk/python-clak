"""Tests for clak._optional dependency helpers."""

import builtins

import pytest

from clak._optional import available, install_hint, optional, require
from clak.exception import ClakUserError

pytestmark = pytest.mark.tags("unit-tests")


def test_install_hint_maps_package_to_extra():
    assert install_hint("yaml") == "pip install 'mrjk.clak[config]'"
    assert install_hint("rich.syntax") == "pip install 'mrjk.clak[markdown]'"
    assert install_hint("docutils.core") == "pip install 'mrjk.clak[rst]'"


def test_optional_returns_submodule():
    mod = optional("json.decoder")
    assert mod is not None and mod.__name__ == "json.decoder"


def test_missing_module(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("rich"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert optional("rich.console") is None
    assert available("rich") is False
    with pytest.raises(ClakUserError) as exc:
        require("rich.console", "Markdown rendering")
    assert str(exc.value) == "Markdown rendering requires the rich package"
    assert exc.value.advice == "Install with: pip install 'mrjk.clak[markdown]'"
