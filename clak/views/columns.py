"""Column specs: parse/normalize CLI and Meta values, resolve and sort.

A column spec is a header name, a 1-based index, or a negative index from
the end (``-1`` = last). Shared by table, list and composite views.
"""

from __future__ import annotations

from collections.abc import Mapping

from clak.views.base import WRAP_MODES

SORT_MODES = frozenset({"asc", "desc"})


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


def normalize_sort_mode(mode, default="asc"):
    """Return True when sort order is descending."""
    if mode is None:
        mode = default
    if not isinstance(mode, str):
        raise TypeError(f"sort_mode must be a string, got {type(mode).__name__}")
    mode = mode.lower()
    if mode not in SORT_MODES:
        raise ValueError(f"sort_mode must be one of {sorted(SORT_MODES)}, got {mode!r}")
    return mode == "desc"


def resolve_column_index(col, headers):
    """Resolve a column spec to a 0-based index in *headers*.

    - str: header name
    - int < 0: index from end (-1 = last column)
    - int > 0: 1-based index (1 = first column)
    - int == 0: rejected
    """
    if isinstance(col, str):
        try:
            return headers.index(col)
        except ValueError as err:
            choices = ", ".join(str(header) for header in headers)
            raise KeyError(
                f"Column {col!r} not found in headers, choices: {choices}"
            ) from err

    if isinstance(col, int):
        if col == 0:
            raise KeyError(
                "Column index 0 is invalid; use 1 for first column or -1 for last"
            )
        if col < 0:
            idx = len(headers) + col
        else:
            idx = col - 1
        if idx < 0 or idx >= len(headers):
            choices = ", ".join(str(header) for header in headers)
            raise KeyError(f"Column index {col} out of range, choices: {choices}")
        return idx

    raise TypeError(f"Column must be a string or int, got {type(col).__name__}")


def resolve_column_keys(columns, headers, *, strict_names=True):
    """Resolve column specs (names / 1-based / negatives) to header keys.

    When *strict_names* is False, string names are kept as-is even if missing
    from *headers* (list views use placeholders for heterogeneous rows).
    Integer specs are always resolved against *headers*.
    """
    if columns is None:
        return list(headers)
    resolved = []
    for col in columns:
        if isinstance(col, int):
            resolved.append(headers[resolve_column_index(col, headers)])
        elif isinstance(col, str):
            if strict_names:
                resolve_column_index(col, headers)
            resolved.append(col)
        else:
            raise TypeError(f"Column must be a string or int, got {type(col).__name__}")
    return resolved


def _cell_sort_key(value):
    """Sort key: numbers before strings; digit strings compare as ints."""
    if isinstance(value, bool):
        return (2, str(value))
    if isinstance(value, (int, float)):
        return (0, value)
    text = "" if value is None else str(value)
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return (0, int(text))
    return (1, text.lower())


def sort_table_rows(rows, headers, sort_columns, sort_mode="asc"):
    """Sort tabular rows by one or more header names or indexes."""
    if not sort_columns or not rows:
        return rows

    reverse = normalize_sort_mode(sort_mode)
    indexes = [resolve_column_index(col, headers) for col in sort_columns]

    def key_fn(row):
        return [_cell_sort_key(row[idx] if idx < len(row) else "") for idx in indexes]

    return sorted(rows, key=key_fn, reverse=reverse)


def default_sort_columns(headers):
    """Default: sort by the first displayed column, ascending."""
    if not headers:
        return None
    return [1]
