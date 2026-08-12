"""Composite view: ordered sections of tables and text."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import List, Optional, Sequence, Tuple

from clak.views.base import (
    DEFAULT_FORMAT_SCOPE,
    DEFAULT_WIDTH_MODE,
    DEFAULT_WRAP_MODE,
    FORMAT_SCOPES,
    OUTPUT_FORMATS,
    ClakView,
    resolve_view_width,
)
from clak.views.table import (
    FeatureFullViewer,
    ListView,
    ShowView,
    _project_item_columns,
    _project_list_columns,
)
from clak.views.table_formatter import require_yaml
from clak.views.text import MarkdownView, PprintView, RawView, RstView

_SHARED_SETTINGS = frozenset({"width", "wrap", "term_width", "stdout_tty"})
_PRIMARY_TABLE_SETTINGS = frozenset(
    {"columns", "sort_columns", "sort_mode", "add_index"}
)
_LIST_ONLY_SETTINGS = frozenset({"expand_keys"})
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

Section = Tuple[str, ClakView, dict]


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _section_kind(view: ClakView) -> str:
    if isinstance(view, ListView):
        return "list"
    if isinstance(view, ShowView):
        return "show"
    if isinstance(view, MarkdownView):
        return "markdown"
    if isinstance(view, RstView):
        return "rst"
    if isinstance(view, RawView):
        return "raw"
    if isinstance(view, PprintView):
        return "pprint"
    return "view"


def _as_section_meta(raw) -> dict:
    """Keep only non-empty ``title`` / ``description`` strings."""
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise TypeError(
            "CompositeView section meta must be a mapping, "
            f"got {type(raw).__name__}"
        )
    meta = {}
    for key in ("title", "description"):
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            meta[key] = text
    return meta


def _format_section_header(meta: Mapping) -> str:
    """Human header: ``=== Title ===`` then optional plain description."""
    lines = []
    title = meta.get("title")
    if title:
        lines.append(f"=== {title} ===")
    description = meta.get("description")
    if description:
        lines.append(description)
    return "\n".join(lines)


def normalize_sections(sections) -> List[Section]:
    """Normalize section specs to ``(name, ClakView, meta)`` triples."""
    if sections is None:
        return []
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
        raise TypeError(
            "CompositeView sections must be a sequence of ClakView or "
            f"(name, ClakView[, meta]), got {type(sections).__name__}"
        )

    result: List[Section] = []
    for index, item in enumerate(sections):
        if isinstance(item, ClakView):
            result.append((f"section_{index}", item, {}))
            continue
        if isinstance(item, (tuple, list)) and len(item) in (2, 3):
            name, view = item[0], item[1]
            if not isinstance(view, ClakView):
                raise TypeError(
                    "CompositeView section view must be a ClakView, "
                    f"got {type(view).__name__}"
                )
            meta = _as_section_meta(item[2] if len(item) == 3 else None)
            result.append((str(name), view, meta))
            continue
        raise TypeError(
            "CompositeView section must be a ClakView or "
            f"(name, ClakView[, meta]), got {type(item).__name__}"
        )
    return result


class CompositeView(ClakView):
    """Render ordered sections (tables and/or text) as one CLI output.

    Human ``view`` mode prints sections separated by a blank line and equalizes
    table outer widths. Machine formats honor ``format_scope``:

    - ``first`` (default): export only the primary section
    - ``all``: export a structured envelope of every section
    """

    settings_default = {
        "width": DEFAULT_WIDTH_MODE,
        "wrap": DEFAULT_WRAP_MODE,
        "format": "view",
        "format_scope": DEFAULT_FORMAT_SCOPE,
        "columns": None,
        "sort_columns": None,
        "sort_mode": "asc",
        "add_index": None,
        "expand_keys": True,
    }

    def __init__(self, sections=None, *, primary: Optional[str] = None, **kwargs):
        super().__init__(payload=sections, **kwargs)
        self.primary_name = primary

    def render(self, *args, stdout=True, **kwargs):
        "Render composite sections"

        payload, settings = self._render(*args, **kwargs)
        sections = normalize_sections(payload)
        if not sections:
            return self._output("", stdout=stdout)

        fmt = settings.pop("format", None) or "view"
        scope = settings.pop("format_scope", None) or DEFAULT_FORMAT_SCOPE
        if not isinstance(scope, str) or scope.lower() not in FORMAT_SCOPES:
            raise ValueError(
                f"format_scope must be one of {sorted(FORMAT_SCOPES)}, got {scope!r}"
            )
        scope = scope.lower()

        primary_name, primary_view, _ = self._resolve_primary(sections)

        if fmt == "view":
            rendered = self._render_view(sections, settings, primary_name)
            return self._output(rendered, stdout=stdout)

        if fmt not in OUTPUT_FORMATS - {"view"}:
            raise ValueError(
                f"Unsupported format {fmt!r}, choose one of: {sorted(OUTPUT_FORMATS)}"
            )

        if scope == "first":
            child_kw = self._settings_for_child(
                primary_view, settings, is_primary=True, format=fmt
            )
            return primary_view.render(stdout=stdout, **child_kw)

        rendered = self._render_envelope(sections, settings, primary_name, fmt)
        return self._output(rendered, stdout=stdout)

    def _resolve_primary(self, sections: Sequence[Section]) -> Section:
        if self.primary_name is None:
            return sections[0]
        for name, view, meta in sections:
            if name == self.primary_name:
                return name, view, meta
        names = [name for name, _, _ in sections]
        raise ValueError(
            f"primary section {self.primary_name!r} not found; available: {names}"
        )

    @staticmethod
    def _settings_for_child(view, settings, *, is_primary, format=None):
        """Build kwargs for a child render; table CLI opts apply to primary only."""
        child = {key: settings[key] for key in _SHARED_SETTINGS if key in settings}
        if format is not None:
            child["format"] = format
        if is_primary and isinstance(view, FeatureFullViewer):
            for key in _PRIMARY_TABLE_SETTINGS:
                if key not in settings:
                    continue
                value = settings[key]
                # ShowView requires a bool; CompositeView default is None (ListView).
                if key == "add_index" and not isinstance(view, ListView):
                    if not isinstance(value, bool):
                        continue
                child[key] = value
            if isinstance(view, ListView):
                for key in _LIST_ONLY_SETTINGS:
                    if key in settings:
                        child[key] = settings[key]
        return child

    def _render_view(self, sections, settings, primary_name):
        equalized = self._equalize_table_width_settings(
            sections, settings, primary_name
        )
        parts = []
        for name, view, meta in sections:
            # Shared table-width budget applies only to table children; text
            # sections keep the original width settings so prose is not
            # reflowed to the table border width.
            child_settings = (
                equalized if isinstance(view, (ShowView, ListView)) else settings
            )
            child_kw = self._settings_for_child(
                view,
                child_settings,
                is_primary=(name == primary_name),
                format="view",
            )
            body = view.render(stdout=False, **child_kw) or ""
            header = _format_section_header(meta)
            if header and body:
                parts.append(f"{header}\n\n{body}")
            elif header:
                parts.append(header)
            elif body:
                parts.append(body)
        return "\n\n".join(parts)

    def _equalize_table_width_settings(self, sections, settings, primary_name):
        """Force table sections to share one outer border width."""
        tables = [
            (name, view)
            for name, view, _meta in sections
            if isinstance(view, (ShowView, ListView))
        ]
        if len(tables) < 2:
            return settings

        mode, term_budget = resolve_view_width(
            width=settings.get("width"),
            term_width=settings.get("term_width"),
            stdout_tty=settings.get("stdout_tty"),
        )

        if mode == "terminal" and term_budget is not None:
            # Already a shared budget for every table child.
            return settings

        measure_settings = dict(settings)
        measure_settings["width"] = "min"
        naturals = []
        for name, view in tables:
            child_kw = self._settings_for_child(
                view,
                measure_settings,
                is_primary=(name == primary_name),
                format="view",
            )
            text = view.render(stdout=False, **child_kw) or ""
            first = text.splitlines()[0] if text else ""
            naturals.append(len(_strip_ansi(first)))

        if not naturals:
            return settings

        max_natural = max(naturals)
        if mode == "auto" and term_budget is not None:
            target = term_budget if max_natural > term_budget else max_natural
        else:
            # min (or auto without budget): equalize to widest natural table
            target = max_natural

        out = dict(settings)
        out["width"] = "terminal"
        out["term_width"] = target
        out["stdout_tty"] = True
        return out

    def _section_data(self, view, settings, *, is_primary):
        """Payload for envelope export (apply primary column projection)."""
        data = view.payload
        if not (is_primary and isinstance(view, FeatureFullViewer)):
            return data
        columns = settings.get("columns")
        if columns is None:
            return data
        if isinstance(view, ListView):
            return _project_list_columns(data, columns)
        if isinstance(view, ShowView):
            return _project_item_columns(data, columns)
        return data

    def _render_envelope(self, sections, settings, primary_name, fmt):
        if fmt == "csv":
            return self._render_envelope_csv(sections, settings, primary_name)

        envelope = {"sections": []}
        for name, view, meta in sections:
            is_primary = name == primary_name
            entry = {
                "name": name,
                "kind": _section_kind(view),
                "data": self._section_data(view, settings, is_primary=is_primary),
            }
            if "title" in meta:
                entry["title"] = meta["title"]
            if "description" in meta:
                entry["description"] = meta["description"]
            envelope["sections"].append(entry)

        if fmt == "json":
            return json.dumps(envelope, indent=2, default=str) + "\n"
        if fmt == "yaml":
            return require_yaml().safe_dump(
                envelope, sort_keys=False, default_flow_style=False
            )
        raise ValueError(f"Unsupported format {fmt!r}")

    def _render_envelope_csv(self, sections, settings, primary_name):
        blocks = []
        for name, view, meta in sections:
            blocks.append(f"# section: {name}")
            if "title" in meta:
                blocks.append(f"# title: {meta['title']}")
            if "description" in meta:
                blocks.append(f"# description: {meta['description']}")
            if isinstance(view, (ShowView, ListView)):
                child_kw = self._settings_for_child(
                    view,
                    settings,
                    is_primary=(name == primary_name),
                    format="csv",
                )
                blocks.append(view.render(stdout=False, **child_kw).rstrip("\n"))
            else:
                payload = view.payload
                blocks.append("" if payload is None else str(payload))
            blocks.append("")
        return "\n".join(blocks).rstrip() + "\n"
