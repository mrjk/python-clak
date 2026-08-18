"""Tests for ClakSettings and plugin hook registration."""

import pytest

from clak import LoggingOptMixin, Parser
from clak.core.plugins import CLI_HOOK_PREFIX, PluginHelpers
from clak.runtime.settings import ClakSettings, apply_debug_logging

pytestmark = pytest.mark.tags("unit-tests")


def test_from_env_reads_clak_env(monkeypatch):
    monkeypatch.setenv("CLAK_DEBUG", "1")
    monkeypatch.setenv("CLAK_COLORS", "0")
    monkeypatch.setenv("CLAK_LOG_COLORS", "1")
    monkeypatch.setenv("CLAK_COLOR_BACKEND", "none")
    settings = ClakSettings.from_env()
    assert settings.debug is True
    assert settings.colors is False
    assert settings.log_colors is True
    assert settings.color_backend == "none"
    assert settings.log_format
    assert isinstance(settings.styles, dict)


def test_current_uses_module_aliases(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_DEBUG", True)
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", False)
    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", True)
    settings = ClakSettings.current()
    assert settings.debug is True
    assert settings.colors is False
    assert settings.log_colors is True


def test_apply_debug_logging_skips_when_not_debug(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_DEBUG", False)
    monkeypatch.setattr("clak.runtime.settings._DEBUG_LOGGING_APPLIED", False)
    apply_debug_logging()
    assert (
        __import__(
            "clak.runtime.settings", fromlist=["_DEBUG_LOGGING_APPLIED"]
        )._DEBUG_LOGGING_APPLIED
        is False
    )


def test_hook_register_uses_hook_list_not_setattr():
    class Host:
        pass

    class Plugin(PluginHelpers):
        def cli_hook__demo(self, instance, ctx, **_):
            return "ok"

        def extra(self, **_):
            return 1

    host = Host()
    plugin = Plugin()
    plugin.hook_register("cli_hook__demo", host)
    plugin.hook_register("extra", host)

    assert not hasattr(host, "cli_hook__demo")
    assert not hasattr(host, "extra")
    assert "cli_hook__demo" in host._cli_hooks
    assert "extra" in host.cli_methods
    assert "extra" not in host._cli_hooks
    assert host.cli_methods["extra"]() == 1


def test_parser_collects_mixin_hooks_at_build():
    class App(LoggingOptMixin, Parser):
        def cli_run(self, **_):
            return None

    app = App(parse=False)
    hook_name = f"{CLI_HOOK_PREFIX}logging"
    assert hook_name in app._cli_hooks
    assert callable(app._cli_hooks[hook_name])
