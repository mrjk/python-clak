"""Tests for CompositeView and CompositeViewMixin."""

import json

import pytest

from clak.parser import Parser
from clak.views import ListView, MarkdownView, RawView, ShowView
from tests.view_fixtures import _has_background_csi, _option_flags

pytestmark = pytest.mark.tags("unit-tests")


# ---------------------------------------------------------------------------
# CompositeView
# ---------------------------------------------------------------------------


def test_composite_view_order_and_blank_separators():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada"}])),
            ("notes", RawView("hello notes")),
            ("more", ListView([{"name": "linus"}])),
        ],
        width="min",
    ).render(stdout=False)

    assert "ada" in out
    assert "hello notes" in out
    assert "linus" in out
    assert "\n\nhello notes\n\n" in out


def test_composite_view_shared_table_width_min():
    from clak.views import CompositeView

    primary = ListView(
        [{"name": "a", "role": "admin", "city": "London"}],
    )
    secondary = ListView([{"n": "x"}])
    out = CompositeView(
        [("primary", primary), ("secondary", secondary)],
        width="min",
    ).render(stdout=False)

    blocks = [b for b in out.split("\n\n") if b.strip()]
    assert len(blocks) == 2
    widths = [len(block.splitlines()[0]) for block in blocks]
    assert widths[0] == widths[1]


def test_composite_format_scope_first_json_matches_primary():
    from clak.views import CompositeView

    rows = [{"name": "ada", "role": "admin"}]
    primary_only = ListView(rows).render(stdout=False, format="json")
    composite = CompositeView(
        [
            ("users", ListView(rows)),
            ("notes", RawView("skip me")),
        ],
        format="json",
        format_scope="first",
    ).render(stdout=False)
    assert json.loads(composite) == json.loads(primary_only)


def test_composite_format_scope_all_envelope_json():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada"}])),
            ("notes", RawView("## Notes")),
        ],
        format="json",
        format_scope="all",
    ).render(stdout=False)
    payload = json.loads(out)
    assert payload == {
        "sections": [
            {"name": "users", "kind": "list", "data": [{"name": "ada"}]},
            {"name": "notes", "kind": "raw", "data": "## Notes"},
        ]
    }


def test_composite_format_scope_all_csv_blocks():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada"}])),
            ("notes", RawView("plain")),
        ],
        format="csv",
        format_scope="all",
    ).render(stdout=False)
    assert "# section: users" in out
    assert "# section: notes" in out
    assert "ada" in out
    assert "plain" in out


def test_composite_primary_override_and_columns():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada", "role": "admin"}])),
            ("related", ListView([{"id": 1, "label": "x"}])),
        ],
        primary="related",
        format="json",
        format_scope="first",
        columns=["label"],
    ).render(stdout=False)
    assert json.loads(out) == [{"label": "x"}]


def test_composite_show_view_primary_with_markdown():
    pytest.importorskip("rich")
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("summary", ShowView({"App": "demo:web", "Name": "Demo"})),
            ("docs", MarkdownView("# Demo README\n\nLong body.")),
        ],
        width="min",
    ).render(stdout=False)
    assert "demo:web" in out
    assert "Long body." in out
    assert "=== Docs ===" not in out


def test_composite_section_title_and_description(monkeypatch):
    from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV
    from clak.views import CompositeView

    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "none")
    out = CompositeView(
        [
            (
                "users",
                ListView([{"name": "ada"}]),
                {
                    "title": "Users",
                    "description": "People with access.",
                },
            ),
            ("notes", RawView("hello notes"), {"title": "Notes"}),
        ],
        width="min",
    ).render(stdout=False)
    assert out.startswith("=== Users ===\nPeople with access.\n\n")
    assert "=== Notes ===\n\nhello notes" in out


def test_composite_section_header_rich_markup(monkeypatch):
    pytest.importorskip("rich")
    from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV
    from clak.views import CompositeView
    from clak.views.base import strip_ansi

    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")
    out = CompositeView(
        [
            (
                "users",
                ListView([{"name": "ada"}]),
                {
                    "title": "[bold]Users[/bold]",
                    "description": "People with [cyan]access[/cyan].",
                },
            ),
        ],
        width="min",
    ).render(stdout=False)
    assert "[bold]" not in out
    assert "[cyan]" not in out
    assert "Users" in out
    assert "access" in out
    assert "\x1b[" in out
    assert not _has_background_csi(out)
    assert "=== Users ===" in strip_ansi(out)


def test_composite_section_header_markup_stays_raw_in_envelope(monkeypatch):
    from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV
    from clak.views import CompositeView

    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")
    out = CompositeView(
        [
            (
                "users",
                ListView([{"name": "ada"}]),
                {
                    "title": "[bold]Users[/bold]",
                    "description": "People with [cyan]access[/cyan].",
                },
            ),
        ],
        format="json",
        format_scope="all",
    ).render(stdout=False)
    payload = json.loads(out)
    assert payload["sections"][0]["title"] == "[bold]Users[/bold]"
    assert payload["sections"][0]["description"] == "People with [cyan]access[/cyan]."


def test_composite_section_header_backend_none_keeps_tags(monkeypatch):
    from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV
    from clak.views import CompositeView

    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "none")
    out = CompositeView(
        [
            (
                "users",
                RawView("body"),
                {"title": "[bold]Users[/bold]"},
            ),
        ]
    ).render(stdout=False)
    assert "=== [bold]Users[/bold] ===" in out
    assert "\x1b[" not in out


def test_composite_section_meta_in_envelope_json():
    from clak.views import CompositeView

    out = CompositeView(
        [
            (
                "users",
                ListView([{"name": "ada"}]),
                {"title": "Users", "description": "People with access."},
            ),
            ("notes", RawView("skip")),
        ],
        format="json",
        format_scope="all",
    ).render(stdout=False)
    payload = json.loads(out)
    assert payload["sections"][0]["title"] == "Users"
    assert payload["sections"][0]["description"] == "People with access."
    assert "title" not in payload["sections"][1]


def test_composite_view_mixin_format_scope_cli(capsys):
    from clak import CompositeViewMixin
    from clak.views import CompositeView

    class App(CompositeViewMixin, Parser):
        def cli_run(self, **_):
            return CompositeView(
                [
                    ("users", ListView([{"name": "ada", "role": "admin"}])),
                    ("notes", RawView("extra")),
                ]
            )

    App(parse=False, add_help=False).dispatch(
        ["--format", "json", "--format-scope", "all"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["sections"]) == 2
    assert payload["sections"][1]["data"] == "extra"


def test_composite_view_mixin_meta_format_scope(capsys):
    from clak import CompositeViewMixin
    from clak.views import CompositeView

    class App(CompositeViewMixin, Parser):
        class Meta:
            view_format_scope = "all"
            view_format = "json"

        def cli_run(self, **_):
            return CompositeView(
                [
                    ("users", ListView([{"name": "ada"}])),
                    ("notes", RawView("meta")),
                ]
            )

    App(parse=False, add_help=False).dispatch([])
    payload = json.loads(capsys.readouterr().out)
    assert payload["sections"][1]["data"] == "meta"


def test_composite_view_mixin_exposes_format_scope_flag():
    from clak import CompositeViewMixin

    class App(CompositeViewMixin, Parser):
        def cli_run(self, **_):
            return None

    assert "--format-scope" in _option_flags(App(parse=False, add_help=False))


def test_composite_unknown_primary_raises():
    from clak.views import CompositeView

    with pytest.raises(ValueError, match="primary section"):
        CompositeView(
            [("users", ListView([{"name": "ada"}]))],
            primary="missing",
        ).render(stdout=False)
