"""Tests for ClakSettings and plugin hook collection."""

import pytest

from clak import LoggingOptMixin, Parser
from clak.core.plugins import CLI_HOOK_PREFIX
from clak.runtime.settings import (
    ClakSettings,
    apply_debug_logging,
    colors_enabled,
    resolve_log_colors,
)
from tests.common import use_settings

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
    use_settings(monkeypatch, debug=True)
    use_settings(monkeypatch, colors=False)
    use_settings(monkeypatch, log_colors=True)
    settings = ClakSettings.current()
    assert settings.debug is True
    assert settings.colors is False
    assert settings.log_colors is True


def test_apply_debug_logging_skips_when_not_debug(monkeypatch):
    use_settings(monkeypatch, debug=False)
    monkeypatch.setattr("clak.runtime.settings._DEBUG_LOGGING_APPLIED", False)
    apply_debug_logging()
    assert (
        __import__(
            "clak.runtime.settings", fromlist=["_DEBUG_LOGGING_APPLIED"]
        )._DEBUG_LOGGING_APPLIED
        is False
    )


def test_parser_collects_mixin_hooks_at_build():
    class App(LoggingOptMixin, Parser):
        def cli_run(self, **_):
            return None

    app = App(parse=False)
    hook_name = f"{CLI_HOOK_PREFIX}logging"
    assert hook_name in app._cli_hooks
    assert callable(app._cli_hooks[hook_name])


def test_colors_enabled_kill_switches(monkeypatch):
    use_settings(monkeypatch, colors=True)
    assert colors_enabled(env={}) is True
    assert colors_enabled(env={"NO_COLOR": "1"}) is False
    assert colors_enabled(env={"NO_COLOR": ""}) is True
    assert colors_enabled(clak_colors=False, env={}) is False
    use_settings(monkeypatch, colors=False)
    assert colors_enabled(env={}) is False


def test_no_color_disables_auto_log_colors(monkeypatch):
    class _Tty:
        def isatty(self):
            return True

    use_settings(monkeypatch, colors=True)
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_log_colors(None, stream=_Tty(), env_value=None) is False
    # Explicit flag still wins over NO_COLOR.
    assert resolve_log_colors(True, stream=_Tty(), env_value=None) is True


def test_settings_current_is_cached_and_replaceable():
    original = ClakSettings.current()
    assert ClakSettings.current() is original
    custom = original.replace(colors=not original.colors)
    assert custom.debug == original.debug
    previous = ClakSettings.set_current(custom)
    try:
        assert previous is original
        assert ClakSettings.current() is custom
        assert colors_enabled(env={}) is custom.colors
    finally:
        ClakSettings.set_current(previous)
    assert ClakSettings.current() is original
