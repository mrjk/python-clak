"""Tests for configurable CLI logging."""

import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from clak import Argument, Parser
from clak.comp import logging as logging_plugin
from clak.comp.logging import LoggingOptMixin, get_app_logger
from clak.exception import ClakAppError
from clak.runtime.settings import resolve_log_colors

pytestmark = pytest.mark.tags("unit-tests")


@pytest.fixture
def logging_mixin():
    return object.__new__(LoggingOptMixin)


def test_explicit_logging_tiers_are_cumulative(logging_mixin):
    tiers = logging_mixin.assemble_user_config([["INFO|app"], ["DEBUG|app"], ["INFO|"]])

    selected = logging_mixin.select_user_config(tiers, req=2)

    assert selected.config["app"]["level"] == logging.DEBUG
    assert selected.config[""]["level"] == logging.INFO
    assert selected.max_level == 2


def test_legacy_logging_groups_expand_to_info_and_debug(logging_mixin):
    tiers = logging_mixin.assemble_user_config([["clak"], [""]])

    assert len(tiers) == 4
    assert (tiers[0][0].logger_name, tiers[0][0].level) == ("clak", logging.INFO)
    assert (tiers[1][0].logger_name, tiers[1][0].level) == ("clak", logging.DEBUG)
    assert (tiers[2][0].logger_name, tiers[2][0].level) == ("", logging.INFO)
    assert (tiers[3][0].logger_name, tiers[3][0].level) == ("", logging.DEBUG)


def test_invalid_logging_configuration_is_rejected(logging_mixin):
    with pytest.raises(ValueError, match="Unknown log level"):
        logging_mixin.assemble_user_config([["LOUD|app"]])

    tiers = logging_mixin.assemble_user_config([["INFO|app"]])
    with pytest.raises(ClakAppError, match="Verbosity must be between"):
        logging_mixin.select_user_config(tiers, req=1)


def test_logger_configuration_filters_to_stderr(capsys):
    get_app_logger(
        loggers={"test.clak": {"level": logging.INFO}},
        level=logging.NOTSET,
    )
    configured_logger = logging.getLogger("test.clak")

    configured_logger.debug("hidden")
    configured_logger.info("visible")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "visible" in captured.err
    assert "hidden" not in captured.err


def test_colors_fall_back_when_coloredlogs_is_unavailable(monkeypatch):
    monkeypatch.setattr(logging_plugin, "coloredlogs", None)

    get_app_logger(colors=True)


def test_log_colors_flag_always_declared():
    assert isinstance(LoggingOptMixin.log_colors, Argument)
    assert LoggingOptMixin.log_colors.kwargs.get("default") is None


def test_resolve_log_colors_cli_overrides_env_and_tty(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", False)
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", False)
    stream = SimpleNamespace(isatty=lambda: False)

    assert resolve_log_colors(True, stream=stream) is True
    assert resolve_log_colors(False, stream=stream) is False


def test_resolve_log_colors_env_overrides_tty(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", True)
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", True)
    stream = SimpleNamespace(isatty=lambda: False)

    assert resolve_log_colors(None, stream=stream) is True

    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", False)
    stream_tty = SimpleNamespace(isatty=lambda: True)
    assert resolve_log_colors(None, stream=stream_tty) is False


def test_resolve_log_colors_auto_uses_tty_and_clak_colors(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", None)
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", True)

    assert resolve_log_colors(None, stream=SimpleNamespace(isatty=lambda: True)) is True
    assert (
        resolve_log_colors(None, stream=SimpleNamespace(isatty=lambda: False)) is False
    )

    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", False)
    assert (
        resolve_log_colors(None, stream=SimpleNamespace(isatty=lambda: True)) is False
    )


def test_resolve_log_colors_env_value_overrides_module_global(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", True)
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", True)
    stream = SimpleNamespace(isatty=lambda: True)

    assert resolve_log_colors(None, stream=stream, env_value=False) is False
    assert resolve_log_colors(None, stream=stream, env_value=None) is True


def test_log_colors_help_uses_meta_env_name():
    class App(LoggingOptMixin, Parser):
        class Meta:
            log_colors_env = "PAASIFY__LOG_COLORS"

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "PAASIFY__LOG_COLORS" in help_text
    assert "CLAK_LOG_COLORS" not in help_text


def test_log_colors_hook_reads_meta_env(monkeypatch):
    monkeypatch.setenv("PAASIFY__LOG_COLORS", "0")
    monkeypatch.setattr("clak.runtime.settings.CLAK_LOG_COLORS", True)
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", True)

    captured = {}

    def _capture_get_app_logger(*args, **kwargs):
        captured["colors"] = kwargs.get("colors")
        return get_app_logger(*args, **kwargs)

    class App(LoggingOptMixin, Parser):
        class Meta:
            log_colors_env = "PAASIFY__LOG_COLORS"
            log_levels = [["INFO|test.branding"]]

        def cli_run(self, **_):
            return None

    with patch("clak.comp.logging.get_app_logger", side_effect=_capture_get_app_logger):
        App(parse=False, add_help=False).dispatch([])

    assert captured.get("colors") is False
