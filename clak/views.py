"""
View classes for command line output formatting.

Classes:
    ClakView: Base view class for rendering command output
        Provides common functionality for formatting and displaying data.

Functions:
    pformat_truncated: Format data with width constraints
        Pretty prints data structures while respecting terminal width limits.

Examples:

    # Tests1 - ShowView
    data_item_dict1 = {
        "name": "World",
        "age": 42,
        "city": "Paris",
    }
    data_item_list1 = [
        "World",
        42,
        "Paris",
    ]

    view = ShowView(data_item_dict1)
    view.render()
    view = ShowView(data_item_list1)
    view.render()

    # Tests2 - DictView
    data_item_dict2 = {
        "name": "World2",
        "age": 43,
        "city": "Berlin",
    }
    data_items_dict_of_dicts = {
        "item1": data_item_dict1,
        "item2": data_item_dict2,
    }
    view = ListView(data_items_dict_of_dicts)
    view.render()

    # Tests3 - ListView
    data_items_list_of_dicts = [
        data_item_dict1,
        data_item_dict2,
    ]
    view = ListView(data_items_list_of_dicts)
    view.render()

"""

# pylint: disable=too-few-public-methods,cyclic-import

from __future__ import annotations

import json
import logging
import re
import textwrap
from collections.abc import Mapping, Sequence
from pprint import pformat
from typing import Any, Optional, Tuple

from clak.exception import ClakUserError
from clak.table_formatter import (
    TableListFormatter,
    TableShowFormatter,
    default_sort_columns,
    format_structured,
    require_yaml,
    resolve_column_keys,
    sort_table_rows,
)

logger = logging.getLogger(__name__)

OUTPUT_FORMATS = frozenset({"view", "yaml", "json", "csv"})
TEXT_FORMATS = frozenset({"view", "raw"})
WIDTH_MODES = frozenset({"min", "auto", "terminal"})
DEFAULT_WIDTH_MODE = "terminal"
WRAP_MODES = frozenset({"last", "all"})
DEFAULT_WRAP_MODE = "last"

_RICH_INSTALL_HINT = "pip install rich"
_DOCUTILS_INSTALL_HINT = "pip install docutils"


class ClakView:
    "Render command line output"

    settings_default = {}

    def __init__(self, payload=None, **kwargs):
        self.settings = kwargs or {}
        self.payload = payload

    def _render(self, *args, **settings):
        "Render data"

        # Fetch best payload
        if len(args) > 0:
            payload = args[0]
        else:
            payload = self.payload

        # Process settings
        _settings = dict(self.settings_default)
        _settings.update(self.settings)
        _settings.update(settings)
        # _settings = SimpleNamespace(**_settings)

        return payload, _settings

    @staticmethod
    def _output(rendered, stdout=True):
        "Optionally print rendered output and always return it."
        if stdout:
            print(rendered)
        return rendered


def merge_view_settings(existing=None, cli_settings=None):
    """Merge CLI view settings over existing view settings.

    CLI values win. When CLI overrides a non-None existing value, log a warning.
    """
    existing = dict(existing or {})
    cli_settings = dict(cli_settings or {})
    merged = dict(existing)
    for key, cli_val in cli_settings.items():
        old_val = existing.get(key, None)
        if old_val is not None and old_val != cli_val:
            logger.warning(
                "CLI option %s=%r overrides view setting %r",
                key,
                cli_val,
                old_val,
            )
        merged[key] = cli_val
    return merged


def parse_columns(value):
    """Parse a comma-separated --columns value into a list of keys/indexes.

    Integer tokens use the same rules as --sort-columns: 1-based indexes
    (1=first), negatives from end (-1=last). Index 0 is rejected at resolve.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"columns must be a string, got {type(value).__name__}")
    cols = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            cols.append(int(part))
        except ValueError:
            cols.append(part)
    return cols


def normalize_columns(value):
    """Normalize Meta.view_columns (string, int index, or sequence) for render."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(
            "view_columns must be a string, int, or sequence, "
            f"got {type(value).__name__}"
        )
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        return parse_columns(value)
    if isinstance(value, (list, tuple)):
        return list(value)
    raise TypeError(
        "view_columns must be a string, int, or sequence, "
        f"got {type(value).__name__}"
    )


def parse_sort_columns(value):
    """Parse --sort-columns: names, 1-based indexes (1=first), or negatives from end."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    if not isinstance(value, str):
        raise TypeError(
            f"sort_columns must be a string or sequence, got {type(value).__name__}"
        )
    cols = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            cols.append(int(part))
        except ValueError:
            cols.append(part)
    return cols


def normalize_sort_columns(value):
    """Normalize Meta.view_sort_columns (string, int index, or sequence)."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(
            "view_sort_columns must be a string, int, or sequence, "
            f"got {type(value).__name__}"
        )
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        return parse_sort_columns(value)
    if isinstance(value, (list, tuple)):
        return list(value)
    raise TypeError(
        "view_sort_columns must be a string, int, or sequence, "
        f"got {type(value).__name__}"
    )


def _project_item_columns(item, columns):
    """Keep original values while projecting selected columns on one row."""
    if isinstance(item, Mapping):
        keys = resolve_column_keys(columns, list(item.keys()), strict_names=False)
        return {key: item[key] for key in keys if key in item}
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        keys = resolve_column_keys(columns, list(range(len(item))))
        return [item[key] for key in keys if isinstance(key, int) and key < len(item)]
    return item


def _project_list_columns(payload, columns):
    """Project columns onto list/dict payloads without table display adapts."""
    if columns is None:
        return payload

    if isinstance(payload, Mapping):
        return {
            key: _project_item_columns(item, columns) for key, item in payload.items()
        }

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return [_project_item_columns(item, columns) for item in payload]

    return payload


def _dump_structured_payload(payload, fmt):
    """Serialize an original payload as json or yaml."""
    if fmt == "json":
        return json.dumps(payload, indent=2, default=str) + "\n"

    if fmt == "yaml":
        return require_yaml().safe_dump(
            payload, sort_keys=False, default_flow_style=False
        )

    raise ValueError(f"Unsupported format {fmt!r}")


def format_show_payload(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    payload,
    fmt,
    columns=None,
    sort_columns=None,
    sort_mode="asc",
    add_index=True,
):
    """Render a single show payload as yaml, json, or csv.

    Sort is applied before serialization (same column rules as the table path).
    """
    if fmt not in OUTPUT_FORMATS - {"view"}:
        raise ValueError(
            f"Unsupported format {fmt!r}, choose one of: {sorted(OUTPUT_FORMATS)}"
        )

    if fmt == "csv":
        rows, headers = TableShowFormatter().process_table(
            payload, columns=columns, add_index=add_index
        )
        if sort_columns is None and headers:
            sort_columns = default_sort_columns(headers)
        if sort_columns:
            rows = sort_table_rows(rows, headers, sort_columns, sort_mode=sort_mode)
        return format_structured(rows, headers, "csv")

    # json / yaml: project original values, then reorder by sort
    if columns is not None:
        payload = _project_item_columns(payload, columns)
    payload = _sort_show_payload(payload, sort_columns, sort_mode)
    return _dump_structured_payload(payload, fmt)


def _sort_show_payload(payload, sort_columns=None, sort_mode="asc"):
    """Reorder a show mapping/sequence using table sort rules (Key/Value rows)."""
    rows, headers = TableShowFormatter().process_table(
        payload, columns=None, add_index=True, remove_tabs=False
    )
    if not rows:
        return payload
    if sort_columns is None:
        sort_columns = default_sort_columns(headers)
    if not sort_columns:
        return payload
    rows = sort_table_rows(rows, headers, sort_columns, sort_mode=sort_mode)
    if isinstance(payload, Mapping):
        return {row[0]: payload[row[0]] for row in rows if row[0] in payload}
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        # Index column is original position; Value is the element
        return [payload[row[0]] for row in rows if isinstance(row[0], int)]
    return payload


def format_list_payload(
    payload,
    fmt,
    columns=None,
    sort_columns=None,
    sort_mode="asc",
):
    """Render a list payload as yaml or json with original values.

    Unlike the table path, this does not fill missing cells with ``"-"``,
    strip tabs, add Index columns, or otherwise adapt values for display.
    Sort is applied to the projected payload before serialization.
    """
    if fmt not in {"json", "yaml"}:
        raise ValueError(f"Unsupported format {fmt!r}, choose one of: ['json', 'yaml']")

    projected = _project_list_columns(payload, columns)
    projected = _sort_list_payload(projected, sort_columns, sort_mode)
    return _dump_structured_payload(projected, fmt)


def _sort_mapping_payload(payload, sort_columns, sort_mode):
    """Sort a dict-of-row-mappings; preserve key association."""
    if not payload:
        return payload
    keys = list(payload.keys())
    values = list(payload.values())
    if not isinstance(values[0], Mapping):
        return payload
    headers = list(values[0].keys())
    if sort_columns is None:
        sort_columns = default_sort_columns(headers)
    if not sort_columns:
        return payload
    rows = [[item.get(header, "") for header in headers] for item in values]
    indexed = [[idx] + row for idx, row in enumerate(rows)]
    remapped = _remap_sort_cols_after_index(sort_columns)
    sorted_indexed = sort_table_rows(
        indexed, ["__idx__"] + headers, remapped, sort_mode=sort_mode
    )
    order = [row[0] for row in sorted_indexed]
    return {keys[i]: values[i] for i in order}


def _sort_sequence_payload(payload, sort_columns, sort_mode):
    """Sort a sequence of rows (mappings or sequences)."""
    if not payload:
        return payload
    first = payload[0]
    if isinstance(first, Mapping):
        return _sort_sequence_of_mappings(list(payload), sort_columns, sort_mode)
    if isinstance(first, Sequence) and not isinstance(first, (str, bytes)):
        headers = list(range(len(first)))
        if sort_columns is None:
            sort_columns = default_sort_columns(headers)
        if not sort_columns:
            return payload
        rows = [list(item) for item in payload]
        return sort_table_rows(rows, headers, sort_columns, sort_mode=sort_mode)
    return payload


def _sort_list_payload(payload, sort_columns=None, sort_mode="asc"):
    """Sort a list/dict-of-rows payload by column specs."""
    if isinstance(payload, Mapping):
        return _sort_mapping_payload(payload, sort_columns, sort_mode)
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return _sort_sequence_payload(payload, sort_columns, sort_mode)
    return payload


def _remap_sort_cols_after_index(sort_columns):
    """Shift 1-based positive indexes by +1 when a leading index column is present."""
    remapped = []
    for col in sort_columns:
        if isinstance(col, int) and col > 0:
            remapped.append(col + 1)
        else:
            remapped.append(col)
    return remapped


def _sort_sequence_of_mappings(items, sort_columns=None, sort_mode="asc"):
    """Sort a list of mapping rows; return original dicts in sorted order."""
    if not items:
        return items
    headers = list(items[0].keys())
    if sort_columns is None:
        sort_columns = default_sort_columns(headers)
    if not sort_columns:
        return items
    rows = [[item.get(header, "") for header in headers] for item in items]
    indexed = [[idx] + row for idx, row in enumerate(rows)]
    remapped = _remap_sort_cols_after_index(sort_columns)
    sorted_indexed = sort_table_rows(
        indexed, ["__idx__"] + headers, remapped, sort_mode=sort_mode
    )
    return [items[row[0]] for row in sorted_indexed]


def resolve_view_width(
    settings: Optional[Mapping[str, Any]] = None,
    *,
    width: Optional[str] = None,
    term_width: Optional[int] = None,
    stdout_tty: Optional[bool] = None,
) -> Tuple[str, Optional[int]]:
    """Resolve effective width mode and optional terminal budget.

    Non-TTY stdout forces ``auto`` / ``terminal`` down to ``min`` (no wrap).
    Returns ``(effective_mode, term_budget_or_none)``.
    """
    settings = dict(settings or {})
    if width is None:
        width = settings.get("width", DEFAULT_WIDTH_MODE)
    if term_width is None:
        term_width = settings.get("term_width")
    if stdout_tty is None:
        stdout_tty = settings.get("stdout_tty")

    mode = width if width is not None else DEFAULT_WIDTH_MODE
    if not isinstance(mode, str):
        raise TypeError(f"width must be a string, got {type(mode).__name__}")
    mode = mode.lower()
    if mode not in WIDTH_MODES:
        raise ValueError(f"width must be one of {sorted(WIDTH_MODES)}, got {mode!r}")

    if mode != "min" and not stdout_tty:
        mode = "min"

    if mode == "min":
        return mode, None

    if term_width is None:
        return "min", None

    return mode, int(term_width)


def pformat_truncated(data, width=None, term_width=None, stdout_tty=None, **_):
    """Pretty-print *data*, optionally wrapping to the resolved view width."""
    mode, term_budget = resolve_view_width(
        width=width if width is not None else DEFAULT_WIDTH_MODE,
        term_width=term_width,
        stdout_tty=stdout_tty,
    )
    if mode == "min" or term_budget is None:
        return pformat(data)

    formatted = pformat(data, width=term_budget)
    return textwrap.fill(formatted, width=term_budget)


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


# Helpers views
# ===================================


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


# Generic views
# ===================================


class FeatureFullViewer(ClakView):
    "Table view base: shared settings for Show and List"

    settings_default = {
        "columns": None,
        "width": DEFAULT_WIDTH_MODE,
        "wrap": DEFAULT_WRAP_MODE,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
        "add_index": None,
    }


class ShowView(FeatureFullViewer):
    "Render show data"

    settings_default = {
        **FeatureFullViewer.settings_default,
        "add_index": True,
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        fmt = settings.pop("format", None) or "view"
        if fmt != "view":
            rendered = format_show_payload(
                payload,
                fmt,
                columns=settings.get("columns"),
                sort_columns=settings.get("sort_columns"),
                sort_mode=settings.get("sort_mode") or "asc",
                add_index=(
                    settings["add_index"]
                    if isinstance(settings.get("add_index"), bool)
                    else True
                ),
            )
            return self._output(rendered, stdout=stdout)

        rendered = TableShowFormatter().render(payload, **settings)
        return self._output(rendered, stdout=stdout)


class ListView(FeatureFullViewer):
    "Render list data"

    settings_default = {
        **FeatureFullViewer.settings_default,
        "expand_keys": True,
        "add_index": None,
    }

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        fmt = settings.pop("format", None) or "view"
        if fmt in {"yaml", "json"}:
            rendered = format_list_payload(
                payload,
                fmt,
                columns=settings.get("columns"),
                sort_columns=settings.get("sort_columns"),
                sort_mode=settings.get("sort_mode") or "asc",
            )
            return self._output(rendered, stdout=stdout)

        rendered = TableListFormatter().render(payload, format=fmt, **settings)
        return self._output(rendered, stdout=stdout)
