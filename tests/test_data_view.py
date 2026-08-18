"""Tests for DataView structured JSON/YAML output."""

import builtins
import json
import re

import pytest

from clak import DataViewMixin, Parser
from clak.exception import ClakUserError
from clak.runtime.rich_style import (
    CLAK_SYNTAX_THEME_ENV,
    DEFAULT_SYNTAX_THEME,
    resolve_syntax_theme,
)
from clak.views import CompositeView, DataView
from clak.views.composite import _section_kind
from clak.views.data import format_data_payload, resolve_data_format

pytestmark = pytest.mark.tags("unit-tests")

PAYLOAD = {"name": "ada", "roles": ["admin", "ops"]}
STRING_PAYLOAD = {
    "title": "Traefik Web",
    "description": "Reverse proxy",
    "enum": ["http", "https"],
}


def _option_flags(app):
    return {opt for action in app.parser._actions for opt in action.option_strings}


def _block_import(monkeypatch, *blocked):
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name in blocked or any(name.startswith(f"{b}.") for b in blocked):
            raise ImportError(f"blocked for test: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)


# ---------------------------------------------------------------------------
# Format resolve + dump helpers
# ---------------------------------------------------------------------------


def test_resolve_data_format_auto_prefers_yaml():
    pytest.importorskip("yaml")
    assert resolve_data_format(None) == "yaml"


def test_resolve_data_format_auto_falls_back_to_json(monkeypatch):
    _block_import(monkeypatch, "yaml")
    assert resolve_data_format(None) == "json"


def test_resolve_data_format_explicit_yaml_missing_raises(monkeypatch):
    _block_import(monkeypatch, "yaml")
    with pytest.raises(ClakUserError) as exc:
        resolve_data_format("yaml")
    assert "yaml" in str(exc.value.message).lower()
    assert "pip install" in (exc.value.advice or "")


def test_resolve_data_format_invalid_raises():
    with pytest.raises(ValueError, match="Unsupported format"):
        resolve_data_format("xml")


def test_format_data_payload_json_pretty_and_compact():
    pretty, fmt = format_data_payload(PAYLOAD, fmt="json", compact=False)
    assert fmt == "json"
    assert pretty == json.dumps(PAYLOAD, indent=2) + "\n"

    compact, fmt = format_data_payload(PAYLOAD, fmt="json", compact=True)
    assert fmt == "json"
    assert compact == json.dumps(PAYLOAD) + "\n"
    assert "\n  " not in compact


def test_format_data_payload_yaml_anchors():
    pytest.importorskip("yaml")
    shared = {"x": 1}
    payload = {"a": shared, "b": shared}

    with_anchors, fmt = format_data_payload(payload, fmt="yaml", anchors=True)
    assert fmt == "yaml"
    assert "&" in with_anchors
    assert "*" in with_anchors

    no_anchors, _ = format_data_payload(payload, fmt="yaml", anchors=False)
    assert "&" not in no_anchors
    assert "*" not in no_anchors
    assert no_anchors.count("x: 1") == 2


# ---------------------------------------------------------------------------
# DataView render
# ---------------------------------------------------------------------------


def test_data_view_auto_yaml(capsys):
    pytest.importorskip("yaml")
    rendered = DataView(PAYLOAD, color=False).render(stdout=False)
    assert "name: ada" in rendered
    assert capsys.readouterr().out == ""


def test_data_view_json_compact():
    rendered = DataView(PAYLOAD, format="json", compact=True, color=False).render(
        stdout=False
    )
    assert rendered.strip() == json.dumps(PAYLOAD)
    assert "\n  " not in rendered


def test_data_view_explicit_yaml_missing_raises(monkeypatch):
    _block_import(monkeypatch, "yaml")
    with pytest.raises(ClakUserError) as exc:
        DataView(PAYLOAD, format="yaml", color=False).render(stdout=False)
    assert (
        "PyYAML" in str(exc.value.message) or "yaml" in str(exc.value.message).lower()
    )


def test_data_view_color_auto_off_without_tty():
    rendered = DataView(PAYLOAD, format="json", color=None, stdout_tty=False).render(
        stdout=False
    )
    assert rendered.startswith("{")
    assert "\x1b[" not in rendered


def test_data_view_color_off_with_clak_colors_disabled(monkeypatch):
    monkeypatch.setattr("clak.runtime.settings.CLAK_COLORS", False)
    rendered = DataView(PAYLOAD, format="json", color=None, stdout_tty=True).render(
        stdout=False
    )
    assert "\x1b[" not in rendered


def test_data_view_explicit_color_missing_rich_raises(monkeypatch):
    _block_import(monkeypatch, "rich")
    with pytest.raises(ClakUserError) as exc:
        DataView(PAYLOAD, format="json", color=True).render(stdout=False)
    assert "rich" in str(exc.value.message).lower()
    assert "pip install" in (exc.value.advice or "")


def test_data_view_auto_color_without_rich_stays_plain(monkeypatch):
    _block_import(monkeypatch, "rich")
    rendered = DataView(PAYLOAD, format="json", color=None, stdout_tty=True).render(
        stdout=False
    )
    assert rendered.startswith("{")
    assert "\x1b[" not in rendered


def test_data_view_explicit_color_with_rich():
    pytest.importorskip("rich")
    rendered = DataView(PAYLOAD, format="json", color=True, stdout_tty=True).render(
        stdout=False
    )
    assert "ada" in rendered
    assert "\x1b[" in rendered


def test_data_view_backend_none_skips_color(monkeypatch):
    pytest.importorskip("rich")
    from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV

    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "none")
    rendered = DataView(PAYLOAD, format="json", color=True, stdout_tty=True).render(
        stdout=False
    )
    assert rendered.startswith("{")
    assert "\x1b[" not in rendered


def _has_background_csi(text: str) -> bool:
    """True if *text* sets a token/pane background (not default-bg or underline)."""
    if "\x1b[48;" in text:
        return True
    for seq in re.findall(r"\x1b\[([0-9;]*)m", text):
        if not seq:
            continue
        for code in seq.split(";"):
            if not code:
                continue
            number = int(code)
            if 40 <= number <= 47 or number == 48 or 100 <= number <= 107:
                return True
    return False


def _spy_syntax_theme(monkeypatch):
    seen = {}
    from clak.runtime.rich_style import resolve_syntax_theme as real

    def _spy(theme=None):
        result = real(theme)
        seen["arg"] = theme
        seen["result"] = result
        return result

    monkeypatch.setattr("clak.runtime.rich_style.resolve_syntax_theme", _spy)
    monkeypatch.setattr("clak.views.rich_style.resolve_syntax_theme", _spy)
    monkeypatch.setattr("clak.views.text.resolve_syntax_theme", _spy)
    return seen


def test_resolve_syntax_theme_default(monkeypatch):
    monkeypatch.delenv(CLAK_SYNTAX_THEME_ENV, raising=False)
    assert resolve_syntax_theme(None) == DEFAULT_SYNTAX_THEME
    assert resolve_syntax_theme("") == DEFAULT_SYNTAX_THEME
    assert resolve_syntax_theme("   ") == DEFAULT_SYNTAX_THEME


def test_resolve_syntax_theme_env(monkeypatch):
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    assert resolve_syntax_theme(None) == "vim"
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "  ")
    assert resolve_syntax_theme(None) == DEFAULT_SYNTAX_THEME


def test_resolve_syntax_theme_explicit_wins_over_env(monkeypatch):
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    assert resolve_syntax_theme("monokai") == "monokai"
    assert resolve_syntax_theme("  monokai  ") == "monokai"


def test_resolve_syntax_theme_rejects_non_string():
    with pytest.raises(TypeError, match="theme must be a string"):
        resolve_syntax_theme(1)


def test_data_view_colored_yaml_json_are_fg_only():
    pytest.importorskip("rich")
    pytest.importorskip("yaml")
    for fmt in ("json", "yaml"):
        rendered = DataView(
            STRING_PAYLOAD, format=fmt, color=True, stdout_tty=True
        ).render(stdout=False)
        assert "\x1b[" in rendered
        assert not _has_background_csi(rendered)
        assert "Traefik Web" in rendered


def test_data_view_monokai_theme_has_no_background_csi():
    pytest.importorskip("rich")
    rendered = DataView(
        STRING_PAYLOAD,
        format="json",
        color=True,
        theme="monokai",
        stdout_tty=True,
    ).render(stdout=False)
    assert "\x1b[" in rendered
    assert not _has_background_csi(rendered)


def test_data_view_color_false_stays_plain():
    pytest.importorskip("rich")
    rendered = DataView(
        STRING_PAYLOAD, format="json", color=False, theme="monokai"
    ).render(stdout=False)
    assert rendered.startswith("{")
    assert "\x1b[" not in rendered


def test_data_view_uses_env_syntax_theme(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    seen = _spy_syntax_theme(monkeypatch)
    DataView(PAYLOAD, format="json", color=True).render(stdout=False)
    assert seen["arg"] is None
    assert seen["result"] == "vim"


def test_data_view_constructor_theme_wins_over_env(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    seen = _spy_syntax_theme(monkeypatch)
    DataView(PAYLOAD, format="json", color=True, theme="monokai").render(stdout=False)
    assert seen["arg"] == "monokai"
    assert seen["result"] == "monokai"


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------


def test_data_view_mixin_auto_renders(capsys):
    pytest.importorskip("yaml")

    class App(DataViewMixin, Parser):
        def cli_run(self, **_):
            return PAYLOAD

    App(parse=False, add_help=False).dispatch(["--no-color"])
    out = capsys.readouterr().out
    assert "name: ada" in out


def test_data_view_mixin_json_compact(capsys):
    class App(DataViewMixin, Parser):
        def cli_run(self, **_):
            return PAYLOAD

    App(parse=False, add_help=False).dispatch(
        ["--format", "json", "--compact", "--no-color"]
    )
    out = capsys.readouterr().out.strip()
    assert out == json.dumps(PAYLOAD)


def test_data_view_mixin_exposes_flags():
    class App(DataViewMixin, Parser):
        def cli_run(self, **_):
            return PAYLOAD

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--format" in flags
    assert "--compact" in flags
    assert "--no-compact" in flags
    assert "--color" in flags
    assert "--no-color" in flags
    assert "--anchors" in flags
    assert "--no-anchors" in flags
    assert "--line-length" not in flags
    assert "--columns" not in flags


def test_data_view_mixin_view_cli_options_false():
    class App(DataViewMixin, Parser):
        class Meta:
            view_cli_options = False

        def cli_run(self, **_):
            return PAYLOAD

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--format" not in flags
    assert "--compact" not in flags
    assert "--color" not in flags
    assert "--anchors" not in flags


def test_data_view_mixin_meta_defaults(capsys):
    class App(DataViewMixin, Parser):
        class Meta:
            view_format = "json"
            view_compact = True
            view_color = False

        def cli_run(self, **_):
            return PAYLOAD

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out.strip()
    assert out == json.dumps(PAYLOAD)


def test_data_view_mixin_meta_syntax_theme(monkeypatch, capsys):
    pytest.importorskip("rich")
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    seen = _spy_syntax_theme(monkeypatch)

    class App(DataViewMixin, Parser):
        class Meta:
            view_format = "json"
            view_color = True
            view_syntax_theme = "monokai"

        def cli_run(self, **_):
            return PAYLOAD

    App(parse=False, add_help=False).dispatch([])
    capsys.readouterr()
    assert seen["arg"] == "monokai"
    assert seen["result"] == "monokai"


def test_data_view_constructor_theme_wins_over_meta(monkeypatch, capsys):
    pytest.importorskip("rich")
    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    seen = _spy_syntax_theme(monkeypatch)

    class App(DataViewMixin, Parser):
        class Meta:
            view_syntax_theme = "default"
            view_color = True

        def cli_run(self, **_):
            return DataView(PAYLOAD, format="json", theme="monokai", color=True)

    App(parse=False, add_help=False).dispatch([])
    capsys.readouterr()
    assert seen["arg"] == "monokai"
    assert seen["result"] == "monokai"


def test_data_view_mixin_no_anchors(capsys):
    pytest.importorskip("yaml")
    shared = {"x": 1}

    class App(DataViewMixin, Parser):
        def cli_run(self, **_):
            return {"a": shared, "b": shared}

    App(parse=False, add_help=False).dispatch(["--no-anchors", "--no-color"])
    out = capsys.readouterr().out
    assert "&" not in out
    assert "*" not in out


# ---------------------------------------------------------------------------
# Composite kind
# ---------------------------------------------------------------------------


def test_composite_section_kind_data():
    assert _section_kind(DataView({"a": 1})) == "data"


def test_composite_includes_data_section():
    pytest.importorskip("yaml")
    out = CompositeView(
        [
            ("primary", DataView({"k": "v"}, color=False)),
        ],
    ).render(stdout=False)
    assert "k: v" in out
