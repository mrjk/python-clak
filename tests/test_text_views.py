"""Tests for Raw, Markdown, and Rst views."""

import pytest

from clak import Parser
from clak.comp.views import (
    ListViewMixin,
    MarkdownViewMixin,
    RawViewMixin,
    RstViewMixin,
)
from clak.exception import ClakUserError
from clak.views import MarkdownView, RawView, RstView
from tests.view_fixtures import USERS, _has_background_csi, _option_flags

pytestmark = pytest.mark.tags("unit-tests")


# ---------------------------------------------------------------------------
# Text views — Raw / Markdown / Rst
# ---------------------------------------------------------------------------


MD_SAMPLE = "# Hello\n\n**bold** and `code`"
MD_FENCE_SAMPLE = """# Title

Use `inline` here.

```yaml
title: Traefik Web
description: Reverse proxy
```

```json
{"title": "Traefik Web"}
```
"""
RST_SAMPLE = "Hello\n=====\n\nThis is **strong** text.\n"


def test_raw_view_mixin_prints_text(capsys):
    class App(RawViewMixin, Parser):
        def cli_run(self, **_):
            return "plain text line"

    App(parse=False, add_help=False).dispatch([])
    assert capsys.readouterr().out.strip() == "plain text line"


def test_raw_view_mixin_exposes_only_line_length():
    class App(RawViewMixin, Parser):
        def cli_run(self, **_):
            return "x"

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--line-length" in flags
    assert "--width" not in flags
    assert "--format" not in flags
    assert "--wrap" not in flags
    assert "--columns" not in flags


def test_markdown_view_mixin_format_raw_without_rich(capsys):
    class App(MarkdownViewMixin, Parser):
        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch(["--format", "raw"])
    out = capsys.readouterr().out
    assert "# Hello" in out
    assert "**bold**" in out


def test_rst_view_mixin_format_raw_without_docutils(capsys):
    class App(RstViewMixin, Parser):
        def cli_run(self, **_):
            return RST_SAMPLE

    App(parse=False, add_help=False).dispatch(["--format", "raw"])
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "=====" in out
    assert "**strong**" in out


def test_markdown_view_mixin_format_choices_are_text_only():
    class App(MarkdownViewMixin, Parser):
        def cli_run(self, **_):
            return MD_SAMPLE

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "--format" in help_text
    assert "raw" in help_text
    assert "yaml" not in help_text
    assert "csv" not in help_text
    assert "--wrap" not in help_text


def test_list_view_mixin_format_choices_remain_table():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "{view,yaml,json,csv}" in help_text or (
        "yaml" in help_text and "json" in help_text and "csv" in help_text
    )
    assert "raw" not in help_text.split("--format")[1].split("\n")[0]


def test_markdown_view_renders_with_rich(capsys):
    pytest.importorskip("rich")

    class App(MarkdownViewMixin, Parser):
        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "# Hello" not in out


def test_markdown_view_backend_none_stays_source(monkeypatch):
    pytest.importorskip("rich")
    from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV

    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "none")
    rendered = MarkdownView(MD_SAMPLE).render(stdout=False)
    assert "# Hello" in rendered
    assert "**bold**" in rendered
    assert "\x1b[" not in rendered


def test_markdown_view_code_is_fg_only():
    pytest.importorskip("rich")
    rendered = MarkdownView(MD_FENCE_SAMPLE).render(stdout=False)
    assert "Traefik Web" in rendered
    assert "inline" in rendered
    assert "\x1b[" in rendered
    assert not _has_background_csi(rendered)


def test_markdown_view_monokai_theme_has_no_background_csi():
    pytest.importorskip("rich")
    rendered = MarkdownView(MD_FENCE_SAMPLE, theme="monokai").render(stdout=False)
    assert "\x1b[" in rendered
    assert not _has_background_csi(rendered)


def test_markdown_view_mixin_meta_syntax_theme(monkeypatch, capsys):
    pytest.importorskip("rich")
    from clak.runtime.rich_style import CLAK_SYNTAX_THEME_ENV, resolve_syntax_theme

    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    seen = {}
    real = resolve_syntax_theme

    def _spy(theme=None):
        result = real(theme)
        seen["arg"] = theme
        seen["result"] = result
        return result

    monkeypatch.setattr("clak.runtime.rich_style.resolve_syntax_theme", _spy)
    monkeypatch.setattr("clak.views.rich_style.resolve_syntax_theme", _spy)
    monkeypatch.setattr("clak.views.text.resolve_syntax_theme", _spy)

    class App(MarkdownViewMixin, Parser):
        class Meta:
            view_syntax_theme = "monokai"

        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    capsys.readouterr()
    assert seen["arg"] == "monokai"
    assert seen["result"] == "monokai"


def test_rst_view_renders_with_docutils(capsys):
    pytest.importorskip("docutils")

    class App(RstViewMixin, Parser):
        def cli_run(self, **_):
            return RST_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "strong" in out
    assert "=====" not in out


def test_rst_view_headings_and_lists_without_html():
    pytest.importorskip("docutils")

    source = (
        "Title\n"
        "=====\n"
        "\n"
        "Intro paragraph.\n"
        "\n"
        "Section\n"
        "-------\n"
        "\n"
        "* alpha\n"
        "* beta\n"
        "\n"
        "1. first\n"
        "2. second\n"
    )
    rendered = RstView(source).render(stdout=False)
    assert "Title" in rendered
    assert "Section" in rendered
    assert "alpha" in rendered
    assert "beta" in rendered
    assert "first" in rendered
    assert "second" in rendered
    assert "<" not in rendered
    assert "=====" not in rendered
    assert "-----" not in rendered


def test_markdown_view_missing_rich_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(ClakUserError) as exc:
        MarkdownView("# hi").render(stdout=False)
    # Undo block before assertions so pytest-clarity can import rich for diffs
    monkeypatch.undo()
    assert "rich" in str(exc.value.message).lower()
    assert "mrjk.clak[markdown]" in (exc.value.advice or "")


def test_rst_view_missing_docutils_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "docutils" or name.startswith("docutils."):
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(ClakUserError) as exc:
        RstView("Title\n=====\n").render(stdout=False)
    monkeypatch.undo()
    assert "docutils" in str(exc.value.message).lower()
    assert "mrjk.clak[rst]" in (exc.value.advice or "")


def test_markdown_view_meta_view_format_raw(capsys):
    class App(MarkdownViewMixin, Parser):
        class Meta:
            view_format = "raw"

        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out
    assert "**bold**" in out


def test_as_text_coerces_non_string():
    assert RawView(42).render(stdout=False) == "42"
    assert RawView(None).render(stdout=False) == ""
