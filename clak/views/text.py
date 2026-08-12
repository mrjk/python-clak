"""Text views: Pprint, Raw, Markdown, Rst."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import re
import textwrap

from clak.exception import ClakUserError
from clak.views.base import (
    DEFAULT_WIDTH_MODE,
    TEXT_FORMATS,
    ClakView,
    pformat_truncated,
    resolve_view_width,
)

_RICH_INSTALL_HINT = "pip install rich"
_DOCUTILS_INSTALL_HINT = "pip install docutils"


def _as_text(payload) -> str:
    """Coerce a payload to text for raw/markdown/rst views."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    return str(payload)


def _wrap_text(text: str, width=None, term_width=None, stdout_tty=None, **_) -> str:
    """Optionally wrap plain text to the resolved view width."""
    mode, term_budget = resolve_view_width(
        width=width if width is not None else DEFAULT_WIDTH_MODE,
        term_width=term_width,
        stdout_tty=stdout_tty,
    )
    if mode == "min" or term_budget is None:
        return text
    return textwrap.fill(text, width=term_budget, replace_whitespace=False)


def require_rich():
    """Import rich for markdown terminal rendering, or raise ClakUserError."""
    try:
        import rich.console  # noqa: F401
        import rich.markdown  # noqa: F401
    except ImportError as err:
        raise ClakUserError(
            "Markdown rendering requires the rich package",
            advice=f"Install with: {_RICH_INSTALL_HINT}",
        ) from err
    import rich.console as rich_console
    import rich.markdown as rich_markdown

    return rich_console, rich_markdown


def require_docutils():
    """Import docutils for RST rendering, or raise ClakUserError."""
    try:
        import docutils.core  # noqa: F401
    except ImportError as err:
        raise ClakUserError(
            "RST rendering requires the docutils package",
            advice=f"Install with: {_DOCUTILS_INSTALL_HINT}",
        ) from err
    import docutils.core as docutils_core

    return docutils_core


def render_markdown_text(text: str, width=None, term_width=None, stdout_tty=None, **_):
    """Render markdown source to terminal text via rich."""
    rich_console, rich_markdown = require_rich()
    mode, term_budget = resolve_view_width(
        width=width if width is not None else DEFAULT_WIDTH_MODE,
        term_width=term_width,
        stdout_tty=stdout_tty,
    )
    console_kwargs = {"force_terminal": True, "soft_wrap": True}
    if mode != "min" and term_budget is not None:
        console_kwargs["width"] = term_budget
    console = rich_console.Console(**console_kwargs)
    with console.capture() as capture:
        console.print(rich_markdown.Markdown(text))
    return capture.get().rstrip("\n")


def render_rst_text(text: str, width=None, term_width=None, stdout_tty=None, **_):
    """Render reStructuredText source to plain text via docutils."""
    docutils_core = require_docutils()
    mode, term_budget = resolve_view_width(
        width=width if width is not None else DEFAULT_WIDTH_MODE,
        term_width=term_width,
        stdout_tty=stdout_tty,
    )
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
    if mode != "min" and term_budget is not None:
        return textwrap.fill(plain, width=term_budget, replace_whitespace=False)
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
        "width": DEFAULT_WIDTH_MODE,
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        rendered = pformat_truncated(payload, **settings)
        return self._output(rendered, stdout=stdout)


class RawView(ClakView):
    "Render payload as plain text"

    settings_default = {
        "width": DEFAULT_WIDTH_MODE,
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
        "width": DEFAULT_WIDTH_MODE,
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
        "width": DEFAULT_WIDTH_MODE,
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
