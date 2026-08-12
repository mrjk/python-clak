"""Text views: Pprint, Raw, Markdown, Rst."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import re
import textwrap

from clak.exception import ClakUserError
from clak.views.base import (
    DEFAULT_LINE_LENGTH,
    TEXT_FORMATS,
    ClakView,
    pformat_truncated,
    resolve_wrap_budget,
)

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


def render_markdown_text(
    text: str, line_length=None, term_width=None, stdout_tty=None, **_
):
    """Render markdown source to terminal text via rich."""
    rich_console, rich_markdown = require_rich()
    wrap, budget = resolve_wrap_budget(line_length, term_width, stdout_tty)
    console_kwargs = {"force_terminal": True, "soft_wrap": True}
    if wrap and budget is not None:
        console_kwargs["width"] = budget
    console = rich_console.Console(**console_kwargs)
    with console.capture() as capture:
        console.print(rich_markdown.Markdown(text))
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
            rendered = render_markdown_text(text, **settings)
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
