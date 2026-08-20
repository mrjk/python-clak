"""Tests for view helper parsers and width/settings merge."""

import logging

import pytest

from clak.views.base import (
    DEFAULT_WIDTH_MODE,
    ClakView,
    merge_view_settings,
    resolve_view_width,
)
from clak.views.table import (
    normalize_wrap,
    normalize_wrap_min,
    parse_columns,
    parse_sort_columns,
    parse_wrap,
)

pytestmark = pytest.mark.tags("unit-tests")


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------


def test_parse_columns_comma_separated_and_ints():
    assert parse_columns("name,age") == ["name", "age"]
    assert parse_columns("1, 3") == [1, 3]
    assert parse_columns("-1,2") == [-1, 2]
    assert parse_columns("name,,role") == ["name", "role"]
    assert parse_columns(None) is None


def test_parse_columns_rejects_non_string():
    with pytest.raises(TypeError, match="columns must be a string"):
        parse_columns(["name", "age"])


def test_parse_sort_columns_alias():
    assert parse_sort_columns("name,role") == ["name", "role"]
    assert parse_sort_columns("-1,-3,1") == [-1, -3, 1]
    assert parse_sort_columns(["city", -1]) == ["city", -1]


def test_parse_wrap_keywords_and_columns():
    assert parse_wrap("last") == "last"
    assert parse_wrap("ALL") == "all"
    assert parse_wrap("First") == "first"
    assert parse_wrap("Path,Src") == ["Path", "Src"]
    assert parse_wrap("-1,Src") == [-1, "Src"]
    assert parse_wrap(["Path", "Src", "Path"]) == ["Path", "Src"]
    assert parse_wrap(None) is None


def test_normalize_wrap_and_wrap_min():
    assert normalize_wrap("last") == "last"
    assert normalize_wrap(("Path", "Src")) == ["Path", "Src"]
    assert normalize_wrap(-1) == [-1]
    assert normalize_wrap_min(12) == 12
    assert normalize_wrap_min({"Path": 24, "Src": 12}) == {"Path": 24, "Src": 12}
    with pytest.raises(ValueError, match="wrap_min must be > 0"):
        normalize_wrap_min(0)
    with pytest.raises(TypeError, match="wrap_min must be"):
        normalize_wrap_min("24")


def test_normalize_sort_columns_accepts_sequence():
    from clak.views.table import normalize_sort_columns

    assert normalize_sort_columns(["name", -1]) == ["name", -1]
    assert normalize_sort_columns("role,-1") == ["role", -1]
    assert normalize_sort_columns(1) == [1]


def test_normalize_columns_accepts_sequence():
    from clak.views.table import normalize_columns

    assert normalize_columns(["name", "role"]) == ["name", "role"]
    assert normalize_columns("name,role") == ["name", "role"]
    assert normalize_columns(1) == [1]
    assert normalize_columns(None) is None


def test_merge_view_settings_logs_info_on_override(caplog):
    with caplog.at_level(logging.INFO):
        merged = merge_view_settings(
            {"columns": ["name"]},
            {"columns": ["age"], "add_index": True},
        )

    assert merged == {"columns": ["age"], "add_index": True}
    assert "overrides view setting" in caplog.text


def test_merge_view_settings_no_log_when_unset(caplog):
    with caplog.at_level(logging.INFO):
        merged = merge_view_settings({}, {"columns": ["name"]})

    assert merged == {"columns": ["name"]}
    assert "overrides view setting" not in caplog.text


def test_clakview_merge_settings_matches_wrapper():
    existing = {"columns": ["name"], "width": "fit"}
    cli = {"columns": ["age"]}
    assert ClakView.merge_settings(existing, cli) == merge_view_settings(existing, cli)


def test_resolve_view_width_modes():
    assert DEFAULT_WIDTH_MODE == "fit"
    assert resolve_view_width(width=None, term_width=80, stdout_tty=True) == (
        "fit",
        80,
    )
    assert resolve_view_width(width="content", term_width=80, stdout_tty=True) == (
        "content",
        None,
    )
    assert resolve_view_width(width="fit", term_width=80, stdout_tty=True) == (
        "fit",
        80,
    )
    assert resolve_view_width(width="terminal", term_width=80, stdout_tty=True) == (
        "terminal",
        80,
    )
    assert resolve_view_width(width="terminal", term_width=80, stdout_tty=False) == (
        "content",
        None,
    )
    assert resolve_view_width(width="fit", term_width=None, stdout_tty=True) == (
        "content",
        None,
    )
    # Legacy aliases
    assert resolve_view_width(width="min", term_width=80, stdout_tty=True) == (
        "content",
        None,
    )
    assert resolve_view_width(width="auto", term_width=80, stdout_tty=True) == (
        "fit",
        80,
    )
