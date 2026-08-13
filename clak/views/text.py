"""Text views: Pprint, Raw, Markdown, Rst."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import re
import textwrap

from clak.exception import ClakUserError
from clak.runtime.settings import resolve_color_backend
from clak.views.base import (
    DEFAULT_LINE_LENGTH,
    TEXT_FORMATS,
    ClakView,
    pformat_truncated,
    resolve_wrap_budget,
)
from clak.views.rich_style import make_rich_console, resolve_syntax_theme, syntax_kwargs

_RICH_INSTALL_HINT = "pip install 'mrjk.clak[markdown]'"
_DOCUTILS_INSTALL_HINT = "pip install 'mrjk.clak[rst]'"


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
    wrap, budget = resolve_wrap_budget(line_length, term_width, stdout_tty)
    if not wrap or budget is None:
        return text
    return textwrap.fill(text, width=budget, replace_whitespace=False)


def require_rich():
    """Import rich for markdown terminal rendering, or raise ClakUserError."""
    try:
        import rich.console  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
        import rich.markdown  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError as err:
        raise ClakUserError(
            "Markdown rendering requires the rich package",
            advice=f"Install with: {_RICH_INSTALL_HINT}",
        ) from err
    import rich.console as rich_console  # pylint: disable=import-outside-toplevel
    import rich.markdown as rich_markdown  # pylint: disable=import-outside-toplevel

    return rich_console, rich_markdown


def require_docutils():
    """Import docutils for RST rendering, or raise ClakUserError."""
    try:
        import docutils.core  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError as err:
        raise ClakUserError(
            "RST rendering requires the docutils package",
            advice=f"Install with: {_DOCUTILS_INSTALL_HINT}",
        ) from err
    import docutils.core as docutils_core  # pylint: disable=import-outside-toplevel

    return docutils_core


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
    rich_console, rich_markdown = require_rich()
    import rich.syntax as rich_syntax  # pylint: disable=import-outside-toplevel

    wrap, budget = resolve_wrap_budget(line_length, term_width, stdout_tty)
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
    docutils_core = require_docutils()
    wrap, budget = resolve_wrap_budget(line_length, term_width, stdout_tty)
    parts = docutils_core.publish_parts(
        source=text,
        writer="html",
        settings_overrides={
            "report_level": 5,
            "halt_level": 5,
            "stylesheet_path": None,
            "embed_stylesheet": False,
        },
    )
    title = parts.get("title") or ""
    body = parts.get("body") or parts.get("html_body") or ""
    chunks = []
    if title:
        chunks.append(_html_to_plain(title) if "<" in title else title.strip())
    if body:
        chunks.append(_html_to_plain(body))
    plain = "\n\n".join(chunk for chunk in chunks if chunk).strip()
    if wrap and budget is not None:
        return textwrap.fill(plain, width=budget, replace_whitespace=False)
    return plain


def _html_to_plain(html: str) -> str:
    """Very small HTML-to-text for docutils HTML writer output."""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", "", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", "", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?i)</h[1-6]\s*>", "\n\n", text)
    text = re.sub(r"(?i)</li\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class PprintView(ClakView):
    "Render any payload with pprint"

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        rendered = pformat_truncated(payload, **settings)
        return self._output(rendered, stdout=stdout)


class RawView(ClakView):
    "Render payload as plain text"

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        text = _as_text(payload)
        rendered = _wrap_text(text, **settings)
        return self._output(rendered, stdout=stdout)


class MarkdownView(ClakView):
    "Render markdown text (or raw source with format=raw)"

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
        "format": "view",
        "theme": None,
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        text = _as_text(payload)
        fmt = settings.pop("format", None) or "view"
        if fmt not in TEXT_FORMATS:
            raise ValueError(
                f"Unsupported format {fmt!r}, choose one of: {sorted(TEXT_FORMATS)}"
            )
        merged_theme = settings.pop("theme", None)
        theme = self.settings.get("theme") or merged_theme
        if fmt == "raw" or resolve_color_backend() == "none":
            rendered = _wrap_text(text, **settings)
        else:
            rendered = render_markdown_text(text, theme=theme, **settings)
        return self._output(rendered, stdout=stdout)


class RstView(ClakView):
    "Render reStructuredText (or raw source with format=raw)"

    settings_default = {
        "line_length": DEFAULT_LINE_LENGTH,
        "format": "view",
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        text = _as_text(payload)
        fmt = settings.pop("format", None) or "view"
        if fmt not in TEXT_FORMATS:
            raise ValueError(
                f"Unsupported format {fmt!r}, choose one of: {sorted(TEXT_FORMATS)}"
            )
        if fmt == "raw":
            rendered = _wrap_text(text, **settings)
        else:
            rendered = render_rst_text(text, **settings)
        return self._output(rendered, stdout=stdout)
