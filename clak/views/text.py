"""Text views: Pprint, Raw, Markdown, Rst."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import textwrap

from clak._optional import require
from clak.runtime.rich_style import (
    make_rich_console,
    resolve_syntax_theme,
    syntax_kwargs,
)
from clak.runtime.settings import resolve_color_backend
from clak.views.base import (
    DEFAULT_LINE_LENGTH,
    TEXT_FORMATS,
    ClakView,
    pformat_truncated,
    resolve_line_length,
)


def _as_text(payload) -> str:
    """Coerce a payload to text for raw/markdown/rst views."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    return str(payload)


def _wrap_text(
    text: str, line_length=None, term_width=None, stdout_tty=None, **_
) -> str:
    """Optionally wrap plain text to the resolved line length."""
    wrap, budget = resolve_line_length(
        line_length=line_length, term_width=term_width, stdout_tty=stdout_tty
    )
    if not wrap or budget is None:
        return text
    return textwrap.fill(text, width=budget, replace_whitespace=False)


_FG_MARKDOWN_CLS = None


def _fg_markdown_class(rich_markdown, rich_syntax):
    """Markdown subclass: fenced/indented code is fg-only Syntax, no pane pad."""
    # pylint: disable=global-statement
    global _FG_MARKDOWN_CLS
    if _FG_MARKDOWN_CLS is not None:
        return _FG_MARKDOWN_CLS

    class FgOnlyCodeBlock(rich_markdown.CodeBlock):
        """Code fence renderer that never paints a theme pane background."""

        def __rich_console__(self, console, options):  # pylint: disable=unused-argument
            code = str(self.text).rstrip()
            yield rich_syntax.Syntax(
                code,
                self.lexer_name,
                word_wrap=True,
                padding=0,
                **syntax_kwargs(self.theme),
            )

    class FgMarkdown(rich_markdown.Markdown):
        """Markdown with fg-only fenced and indented code blocks."""

        elements = {
            **rich_markdown.Markdown.elements,
            "fence": FgOnlyCodeBlock,
            "code_block": FgOnlyCodeBlock,
        }

    _FG_MARKDOWN_CLS = FgMarkdown
    return FgMarkdown


def render_markdown_text(
    text: str,
    line_length=None,
    term_width=None,
    stdout_tty=None,
    theme=None,
    **_,
):
    """Render markdown source to terminal text via rich (fg-only code)."""
    rich_console = require("rich.console", "Markdown rendering")
    rich_markdown = require("rich.markdown", "Markdown rendering")
    import rich.syntax as rich_syntax  # pylint: disable=import-outside-toplevel

    wrap, budget = resolve_line_length(
        line_length=line_length, term_width=term_width, stdout_tty=stdout_tty
    )
    width = budget if wrap and budget is not None else None
    console = make_rich_console(rich_console, width=width)
    resolved = resolve_syntax_theme(theme)
    markdown_cls = _fg_markdown_class(rich_markdown, rich_syntax)
    with console.capture() as capture:
        console.print(
            markdown_cls(
                text,
                code_theme=resolved,
                inline_code_theme=resolved,
            )
        )
    return capture.get().rstrip("\n")


def render_rst_text(text: str, line_length=None, term_width=None, stdout_tty=None, **_):
    """Render reStructuredText source to plain text via docutils."""
    docutils_core = require("docutils.core", "RST rendering")
    wrap, budget = resolve_line_length(
        line_length=line_length, term_width=term_width, stdout_tty=stdout_tty
    )
    document = docutils_core.publish_doctree(
        source=text,
        settings_overrides={
            "report_level": 5,
            "halt_level": 5,
        },
    )
    plain = _rst_doctree_to_text(document).strip()
    if wrap and budget is not None:
        return textwrap.fill(plain, width=budget, replace_whitespace=False)
    return plain


def _rst_doctree_to_text(node) -> str:
    """Walk a docutils doctree into readable plain text."""
    import docutils.nodes as docnodes  # pylint: disable=import-outside-toplevel

    def walk(n, list_prefix=None):
        if isinstance(n, (docnodes.system_message, docnodes.comment)):
            return ""
        if isinstance(n, docnodes.Text):
            return str(n)

        children = getattr(n, "children", [])
        if isinstance(n, (docnodes.title, docnodes.subtitle, docnodes.paragraph)):
            text = "".join(walk(c) for c in children).strip()
        elif isinstance(n, docnodes.literal_block):
            text = "".join(walk(c) for c in children).rstrip()
        elif isinstance(n, docnodes.bullet_list):
            text = "\n".join(walk(child, list_prefix="- ") for child in children)
        elif isinstance(n, docnodes.enumerated_list):
            text = "\n".join(
                walk(child, list_prefix=f"{idx}. ")
                for idx, child in enumerate(children, 1)
            )
        elif isinstance(n, docnodes.list_item):
            body = "\n".join(part for part in (walk(c) for c in children) if part)
            prefix = list_prefix or "- "
            lines = body.split("\n") if body else [""]
            out = [prefix + lines[0]]
            indent = " " * len(prefix)
            out.extend(f"{indent}{line}" if line else line for line in lines[1:])
            text = "\n".join(out)
        elif isinstance(n, (docnodes.document, docnodes.section, docnodes.block_quote)):
            parts = [walk(c) for c in children]
            text = "\n\n".join(part for part in parts if part)
        else:
            parts = [walk(c) for c in children]
            text = "".join(part for part in parts if part)
        return text

    return walk(node)


class PprintView(ClakView):
    "Render any payload with pprint"

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
    }

    def to_text(self, payload, settings):
        return pformat_truncated(payload, **settings)


class RawView(ClakView):
    "Render payload as plain text"

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
    }

    def to_text(self, payload, settings):
        return _wrap_text(_as_text(payload), **settings)


class _MarkupView(ClakView):
    """Markup source rendered for the terminal, or raw with ``format=raw``."""

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
        "format": "view",
    }

    def to_text(self, payload, settings):
        text = _as_text(payload)
        fmt = settings.pop("format", None) or "view"
        if fmt not in TEXT_FORMATS:
            raise ValueError(
                f"Unsupported format {fmt!r}, choose one of: {sorted(TEXT_FORMATS)}"
            )
        if fmt == "raw":
            return _wrap_text(text, **settings)
        return self.render_markup(text, settings)

    def render_markup(self, text: str, settings: dict) -> str:
        """Render markup *text* for the terminal."""
        raise NotImplementedError


class MarkdownView(_MarkupView):
    "Render markdown text (or raw source with format=raw)"

    settings_default = {**_MarkupView.settings_default, "theme": None}
    instance_settings = ("theme",)

    def render_markup(self, text, settings):
        if resolve_color_backend() == "none":
            return _wrap_text(text, **settings)
        return render_markdown_text(text, **settings)


class RstView(_MarkupView):
    "Render reStructuredText (or raw source with format=raw)"

    def render_markup(self, text, settings):
        return render_rst_text(text, **settings)
