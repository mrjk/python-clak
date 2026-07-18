"""Tests for configurable CLI logging."""

import logging

import pytest

from clak.comp import logging as logging_plugin
from clak.comp.logging import LoggingOptMixin, get_app_logger
from clak.exception import ClakAppError


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
