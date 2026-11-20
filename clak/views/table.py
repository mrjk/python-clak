"""Table views: ShowView, ListView, and structured payload helpers."""

# pylint: disable=too-few-public-methods,cyclic-import

from __future__ import annotations

from collections.abc import Mapping, Sequence

from clak.views.base import (
    DEFAULT_WIDTH_MODE,
    DEFAULT_WRAP_MODE,
    OUTPUT_FORMATS,
    WRAP_MODES,
    ClakView,
)
from clak.views.serialize import dump
from clak.views.table_formatter import (
    TableListFormatter,
    TableShowFormatter,
    default_sort_columns,
    format_structured,
    resolve_column_keys,
    sort_table_rows,
)


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


def _normalize_column_spec(value, label, parse_str, parse_seq=list):
    """Normalize a Meta column spec: None, int index, string, or sequence."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(
            f"{label} must be a string, int, or sequence, got {type(value).__name__}"
        )
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        return parse_str(value)
    if isinstance(value, (list, tuple)):
        return parse_seq(value)
    raise TypeError(
        f"{label} must be a string, int, or sequence, got {type(value).__name__}"
    )


def normalize_columns(value):
    """Normalize Meta.view_columns (string, int index, or sequence) for render."""
    return _normalize_column_spec(value, "view_columns", parse_columns)


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
    return parse_columns(value)


def normalize_sort_columns(value):
    """Normalize Meta.view_sort_columns (string, int index, or sequence)."""
    return _normalize_column_spec(value, "view_sort_columns", parse_sort_columns)


def _dedupe_wrap_specs(specs):
    """Drop duplicate wrap column specs, keeping first-seen order."""
    seen = set()
    out = []
    for spec in specs:
        if spec in seen:
            continue
        seen.add(spec)
        out.append(spec)
    return out


def parse_wrap(value):
    """Parse --wrap: keyword last/all/first, or flexible column specs.

    Keywords are recognized only when they are the entire value (case
    insensitive). Otherwise the value is a comma-separated column list
    (same rules as --columns). Listed columns expand or shrink to fit
    the terminal; other columns stay content-sized.
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        specs = _dedupe_wrap_specs(list(value))
        if not specs:
            raise ValueError("wrap column list must not be empty")
        return specs
    if not isinstance(value, str):
        raise TypeError(
            f"wrap must be a string or sequence, got {type(value).__name__}"
        )
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.lower() in WRAP_MODES:
        return stripped.lower()
    cols = parse_columns(stripped)
    if not cols:
        raise ValueError("wrap column list must not be empty")
    return _dedupe_wrap_specs(cols)


def normalize_wrap(value):
    """Normalize Meta.view_wrap (keyword or flexible column specs)."""
    return _normalize_column_spec(value, "view_wrap", parse_wrap, parse_seq=parse_wrap)


def normalize_wrap_min(value):
    """Normalize Meta.view_wrap_min: positive int or column-spec mapping."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(
            "wrap_min must be a positive int or mapping, " f"got {type(value).__name__}"
        )
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("wrap_min must be > 0")
        return value
    if isinstance(value, Mapping):
        out = {}
        for key, val in value.items():
            if isinstance(key, bool) or not isinstance(key, (str, int)):
                raise TypeError(
                    "wrap_min keys must be column names or indexes, "
                    f"got {type(key).__name__}"
                )
            if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
                raise ValueError(
                    f"wrap_min[{key!r}] must be a positive int, got {val!r}"
                )
            out[key] = val
        return out
    raise TypeError(
        "wrap_min must be a positive int or mapping, " f"got {type(value).__name__}"
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
    return dump(payload, fmt)


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
    return dump(projected, fmt)


def _sorted_mapping_order(items, sort_columns, sort_mode):
    """Row indexes of mapping *items* in sorted order, or None if unsorted."""
    headers = list(items[0].keys())
    if sort_columns is None:
        sort_columns = default_sort_columns(headers)
    if not sort_columns:
        return None
    indexed = [
        [idx] + [item.get(header, "") for header in headers]
        for idx, item in enumerate(items)
    ]
    sorted_indexed = sort_table_rows(
        indexed,
        ["__idx__"] + headers,
        _remap_sort_cols_after_index(sort_columns),
        sort_mode=sort_mode,
    )
    return [row[0] for row in sorted_indexed]


def _sort_mapping_payload(payload, sort_columns, sort_mode):
    """Sort a dict-of-row-mappings; preserve key association."""
    keys = list(payload.keys())
    values = list(payload.values())
    if not values or not isinstance(values[0], Mapping):
        return payload
    order = _sorted_mapping_order(values, sort_columns, sort_mode)
    if order is None:
        return payload
    return {keys[i]: values[i] for i in order}


def _sort_sequence_payload(payload, sort_columns, sort_mode):
    """Sort a sequence of rows (mappings or sequences)."""
    if not payload:
        return payload
    first = payload[0]
    if isinstance(first, Mapping):
        items = list(payload)
        order = _sorted_mapping_order(items, sort_columns, sort_mode)
        return items if order is None else [items[i] for i in order]
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


class TableView(ClakView):  # pylint: disable=abstract-method
    "Table view base: shared settings for Show and List"

    settings_default = {
        "columns": None,
        "width": DEFAULT_WIDTH_MODE,
        "wrap": DEFAULT_WRAP_MODE,
        "wrap_min": None,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
        "add_index": None,
        "yaml_cells": True,
    }


class ShowView(TableView):
    "Render show data"

    settings_default = {
        **TableView.settings_default,
        "add_index": True,
    }

    def to_text(self, payload, settings):
        fmt = settings.pop("format", None) or "view"
        if fmt == "view":
            return TableShowFormatter().render(payload, **settings)
        add_index = settings.get("add_index")
        return format_show_payload(
            payload,
            fmt,
            columns=settings.get("columns"),
            sort_columns=settings.get("sort_columns"),
            sort_mode=settings.get("sort_mode") or "asc",
            add_index=add_index if isinstance(add_index, bool) else True,
        )


class ListView(TableView):
    "Render list data"

    settings_default = {
        **TableView.settings_default,
        "expand_keys": True,
        "add_index": None,
    }

    def to_text(self, payload, settings):
        fmt = settings.pop("format", None) or "view"
        if fmt in {"yaml", "json"}:
            return format_list_payload(
                payload,
                fmt,
                columns=settings.get("columns"),
                sort_columns=settings.get("sort_columns"),
                sort_mode=settings.get("sort_mode") or "asc",
            )
        return TableListFormatter().render(payload, format=fmt, **settings)
