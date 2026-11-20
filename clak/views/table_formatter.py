"""
Table view classes for pretty-printing data structures.

Classes:
    _TableFormatter: Abstract base class for table views
        Provides common functionality for rendering data in tabular format.
        
    TableShowFormatter: Table view for single data items
        Renders individual dictionaries or sequences as tables.
        
    TableListFormatter: Table view for lists of data items 
        Renders collections of dictionaries or sequences as tables.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

from clak._optional import optional
from clak.common import replace_tabs
from clak.runtime.settings import ClakSettings
from clak.views.base import (
    DEFAULT_WIDTH_MODE,
    DEFAULT_WRAP_MODE,
    OUTPUT_FORMATS,
    resolve_view_width,
    strip_ansi,
)
from clak.views.columns import (
    default_sort_columns,
    normalize_wrap,
    normalize_wrap_min,
    resolve_column_index,
    resolve_column_keys,
    sort_table_rows,
)
from clak.views.serialize import dump, dump_csv, dump_yaml


def _new_table():
    """A PrettyTable, or a ColorTable when Clak colors are enabled.

    Chosen at render time so ``ClakSettings.set_current()`` is honored.
    ColorTable uses colorama, which patches stdout/stderr and appends a reset
    code to each line: never use it when colors are off (regression tests).
    """
    # pylint: disable=import-outside-toplevel
    if ClakSettings.current().colors:
        try:
            from prettytable.colortable import ColorTable, Themes

            return ColorTable(theme=Themes.GLARE_REDUCTION)
        except ImportError:
            pass
    from prettytable import PrettyTable

    return PrettyTable()


def format_structured(rows, headers, fmt):
    """Render tabular rows as yaml, json, or csv (newline-terminated)."""
    if fmt not in OUTPUT_FORMATS - {"view"}:
        raise ValueError(
            f"Unsupported format {fmt!r}, choose one of: {sorted(OUTPUT_FORMATS)}"
        )
    if fmt == "csv":
        return dump_csv(rows, headers)
    return dump([dict(zip(headers, row)) for row in rows], fmt) + "\n"


def _apply_prettytable_width(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    table,
    width=DEFAULT_WIDTH_MODE,
    term_width=None,
    stdout_tty=None,
    wrap="last",
    wrap_min=None,
):
    """Apply content/fit/terminal width modes to a PrettyTable instance."""
    mode, term_budget = resolve_view_width(
        width=width, term_width=term_width, stdout_tty=stdout_tty
    )
    if mode == "content" or term_budget is None:
        return

    wrap_spec = normalize_wrap(wrap if wrap is not None else DEFAULT_WRAP_MODE)
    if wrap_spec is None:
        wrap_spec = DEFAULT_WRAP_MODE
    wrap_min = normalize_wrap_min(wrap_min)

    if isinstance(wrap_spec, str) and wrap_spec == "all":
        if mode == "fit":
            table.max_table_width = term_budget
        elif mode == "terminal":
            table.min_table_width = term_budget
            table.max_table_width = term_budget
        return

    wrap_fields = _resolve_wrap_fields(wrap_spec, list(table.field_names))
    _apply_column_wrap(
        table,
        mode=mode,
        term_width=term_budget,
        wrap_fields=wrap_fields,
        wrap_min=wrap_min,
    )


def _resolve_wrap_fields(wrap_spec, headers):
    """Resolve wrap keyword or column specs to displayed header names."""
    if not headers:
        return []
    if isinstance(wrap_spec, str):
        key = wrap_spec.lower()
        if key == "last":
            return [headers[-1]]
        if key == "first":
            return [headers[0]]
        raise ValueError(
            f"wrap must be last, first, all, or column specs, got {wrap_spec!r}"
        )

    fields = []
    seen = set()
    for col in wrap_spec:
        field = headers[resolve_column_index(col, headers)]
        if field in seen:
            continue
        seen.add(field)
        fields.append(field)
    return fields


def _resolve_wrap_min_map(wrap_min, headers):
    """Resolve wrap_min to a field-name map, or a global int, or None."""
    if wrap_min is None or isinstance(wrap_min, int):
        return wrap_min
    resolved = {}
    for key, val in wrap_min.items():
        field = headers[resolve_column_index(key, headers)]
        resolved[field] = val
    return resolved


def _wrap_column_floor(field, natural_width, wrap_min):
    """Sequential-shrink floor: max(header, wrap_min, 1), capped at natural."""
    header_len = len(str(field))
    requested = None
    if isinstance(wrap_min, int):
        requested = wrap_min
    elif isinstance(wrap_min, Mapping):
        requested = wrap_min.get(field)
    floor = max(header_len, requested if requested is not None else 0, 1)
    return min(floor, natural_width)


def _shrink_wrap_widths(widths, wrap_fields, wrap_min, overflow):
    """Shrink wrap columns in order down to floor, then dump leftover."""
    if overflow <= 0:
        return
    for field in wrap_fields:
        if overflow <= 0:
            break
        floor = _wrap_column_floor(field, widths[field], wrap_min)
        reducible = widths[field] - floor
        if reducible <= 0:
            continue
        take = min(overflow, reducible)
        widths[field] -= take
        overflow -= take
    if overflow > 0:
        last = wrap_fields[-1]
        widths[last] = max(1, widths[last] - overflow)


def _pin_column_widths(field_names, natural_widths, widths, wrap_fields):
    """Build PrettyTable min/max maps: wrap cols use computed width, others frozen."""
    wrap_set = set(wrap_fields)
    min_width = {}
    max_width = {}
    for field, col_width in zip(field_names, natural_widths):
        pinned = widths[field] if field in wrap_set else col_width
        min_width[field] = pinned
        max_width[field] = pinned
    return min_width, max_width


def _apply_column_wrap(
    table, mode, term_width, wrap_fields, wrap_min
):  # pylint: disable=too-many-locals
    """Fit table by shrinking wrap columns in order, then dumping leftover."""
    if not table.field_names or not wrap_fields:
        return

    measured = table.get_string()
    natural_widths = list(table._widths)  # pylint: disable=protected-access
    if not natural_widths:
        return

    plain = strip_ansi(measured)
    border_line = plain.splitlines()[0] if plain else ""
    natural_border = len(border_line)

    if mode == "fit" and natural_border <= term_width:
        return

    widths = dict(zip(table.field_names, natural_widths))
    min_map = _resolve_wrap_min_map(wrap_min, list(table.field_names))
    _shrink_wrap_widths(widths, wrap_fields, min_map, natural_border - term_width)
    min_width, max_width = _pin_column_widths(
        table.field_names, natural_widths, widths, wrap_fields
    )

    if mode == "terminal":
        decorations = natural_border - sum(natural_widths)
        current = decorations + sum(widths[field] for field in table.field_names)
        pad = term_width - current
        if pad > 0:
            first = wrap_fields[0]
            widths[first] += pad
            min_width[first] = widths[first]
            max_width[first] = widths[first]

    # PrettyTable 3.x min_width/max_width setters take a single int;
    # per-column dicts go on the private maps. Table-level min/max stay on
    # wrap=all only; pins already encode the budget here.
    table._min_width = min_width  # pylint: disable=protected-access
    table._max_width = max_width  # pylint: disable=protected-access

    if mode != "terminal":
        return

    rendered = strip_ansi(table.get_string())
    border_line = rendered.splitlines()[0] if rendered else ""
    delta = term_width - len(border_line)
    if delta <= 0:
        return
    first = wrap_fields[0]
    widths[first] += delta
    min_width[first] = widths[first]
    max_width[first] = widths[first]
    table._min_width = min_width  # pylint: disable=protected-access
    table._max_width = max_width  # pylint: disable=protected-access


class _TableFormatter(ABC):
    "Table view"

    view_options = {
        "columns": None,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
        "width": DEFAULT_WIDTH_MODE,
        "wrap": "last",
        "wrap_min": None,
        "yaml_cells": True,
    }

    def __init__(self, data=None, columns=None, **view_options):

        # Init and update view options
        self.view_options = dict(self.view_options)
        self.view_options.update(view_options)

        # Directly render data if provided
        if data is not None:
            self.render(data, stdout=True, columns=columns)

    def render(self, data, stdout=False, **kwargs):
        "Render data, return or print"

        if not isinstance(data, (list, dict)):
            raise ValueError(
                f"Data must be a list or dict, got {type(data).__name__}: {data}"
            )

        out = self.table_render_show(data, **kwargs)
        if stdout:
            print(out)
        return out

    def table_render_show(
        self, data, **view_options
    ):  # pylint: disable=too-many-locals
        "Create a PrettyTable instance, configure it and print it"

        _view_options = dict(self.view_options)
        _view_options.update(view_options)

        fmt = _view_options.pop("format", "view") or "view"
        sort_columns = _view_options.pop("sort_columns", None)
        sort_mode = _view_options.pop("sort_mode", "asc") or "asc"
        width = _view_options.pop("width", DEFAULT_WIDTH_MODE)
        wrap = _view_options.pop("wrap", "last")
        wrap_min = _view_options.pop("wrap_min", None)
        term_width = _view_options.pop("term_width", None)
        stdout_tty = _view_options.pop("stdout_tty", None)
        yaml_cells = _view_options.pop("yaml_cells", True)

        # YAML cells are a display aid: never applied to yaml/json/csv output
        data_table, headers = self.process_table(
            data, yaml_cells=bool(yaml_cells) and fmt == "view", **_view_options
        )
        self.validate_table_data(data_table)

        if sort_columns is None and headers:  # [] = keep the input order
            sort_columns = default_sort_columns(headers)

        if sort_columns:
            data_table = sort_table_rows(
                data_table, headers, sort_columns, sort_mode=sort_mode
            )

        if fmt != "view":
            return format_structured(data_table, headers, fmt)

        table = _new_table()
        table.field_names = headers
        table.align = "l"
        for line in data_table:
            table.add_row(line)

        _apply_prettytable_width(
            table,
            width=width,
            term_width=term_width,
            stdout_tty=stdout_tty,
            wrap=wrap,
            wrap_min=wrap_min,
        )

        # Report output
        return table.get_string()

    def validate_table_data(self, data):
        "Validate table data of raise exception"

        if not isinstance(data, Sequence):
            raise ValueError(f"Data must be a list of lists, got {type(data)}")

        count = None
        for idx, line in enumerate(data):

            if not isinstance(line, Sequence):
                raise ValueError(f"Line {idx} must be a list, got {type(line)}")

            if count is None:
                count = len(line)
            elif count != len(line):
                raise ValueError(
                    f"All lines must have the same number of columns, "
                    f"got {count} vs current line {idx}: {len(line)}"
                )

    @abstractmethod
    def process_table(self, data):
        "Process table data"
        raise NotImplementedError("Subclass must implement this method")


################## Public classes


def yaml_cell(value):
    "Complex values (mapping, list) as block yaml text, so a table cell stays readable."
    if not (isinstance(value, (Mapping, list, tuple)) and value):
        return value
    yaml = optional("yaml")
    if yaml is None:
        return value
    return dump_yaml(_plain(value), yaml=yaml, allow_unicode=True)


def _plain(value):
    "Make `value` safe_dump friendly (paths, tuples, mappings, unknown objects)."
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class TableShowFormatter(_TableFormatter):
    "Table show item"

    view_options = {
        "add_index": True,
        "columns": None,
        "remove_tabs": True,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
        "width": DEFAULT_WIDTH_MODE,
        "wrap": "last",
        "wrap_min": None,
        "yaml_cells": True,
    }

    def process_table(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        data,
        columns=None,
        add_index=True,
        remove_tabs=True,
        yaml_cells=False,
        **_,
    ):
        "Restructure data to fit to item view"

        choices = None
        index_name = "Item"
        if isinstance(data, Mapping):
            choices = list(data.keys())
            index_name = "Key"
        elif isinstance(data, Sequence):
            choices = list(range(len(data)))
            index_name = "Index"

        if columns is None:
            columns = choices
        else:
            columns = resolve_column_keys(columns, choices)

        if not isinstance(add_index, bool):
            raise TypeError(f"add_index must be a bool, got {type(add_index).__name__}")
        ret = []
        for key in columns:
            try:
                # ret.append([key, data[key]])
                value = data[key]
            except (IndexError, KeyError, TypeError):
                choices = ", ".join(str(choice) for choice in choices)
                raise KeyError(
                    f"Key {key} not found in data, choices: {choices}"
                ) from None

            if remove_tabs is not False:
                value = replace_tabs(value, remove_tabs)
            if yaml_cells:
                value = yaml_cell(value)

            if add_index:
                ret.append([key, value])
            else:
                ret.append([value])

        columns = ["Value"]
        if add_index:
            columns = [index_name, "Value"]

        return ret, columns


class TableListFormatter(_TableFormatter):
    "Table list items"

    view_options = {
        "add_index": None,
        "columns": None,
        "expand_keys": True,
        "remove_tabs": True,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
        "width": DEFAULT_WIDTH_MODE,
        "wrap": "last",
        "wrap_min": None,
        "yaml_cells": True,
    }

    # pylint: disable=too-many-branches,too-many-arguments,too-many-positional-arguments,too-many-statements
    def process_table(
        self,
        data,
        columns=None,
        add_index=None,
        expand_keys=True,
        remove_tabs=True,
        yaml_cells=False,
        **_,
    ):
        "Restructure data to fit to list view"

        add_index = add_index if isinstance(add_index, bool) else not expand_keys

        if not expand_keys and columns is not None:
            raise ValueError(
                f"Cannot specify columns when expand_keys is False: {columns}"
            )

        ret = []
        columns_resolved = False

        def _process_expanded_item(idx, item, columns):
            row = [idx] if add_index else []

            for field in columns:
                if isinstance(item, Mapping):
                    value = item.get(field, "-")
                else:
                    try:
                        value = item[field]
                    except (IndexError, KeyError, TypeError):
                        value = "-"
                if remove_tabs is not False:
                    value = replace_tabs(value, remove_tabs)
                row.append(yaml_cell(value) if yaml_cells else value)
            ret.append(row)

        def _resolve_item_columns(item, cols):
            nonlocal columns_resolved
            if columns_resolved:
                return cols
            if isinstance(item, Mapping):
                available = list(item.keys())
            else:
                available = list(range(0, len(item)))
            columns_resolved = True
            if cols is None:
                return available
            return resolve_column_keys(cols, available, strict_names=False)

        _default_columns = ["Key", "Value"]
        if isinstance(data, Mapping):
            for idx, value in data.items():
                if not expand_keys:
                    ret.append([idx, yaml_cell(value) if yaml_cells else value])
                else:
                    if not isinstance(value, Mapping):
                        if hasattr(value, "__dict__"):
                            # Automatically explode object with __dict__ method
                            value = value.__dict__
                        else:
                            value = {
                                "Key": idx,
                                "Value": value,
                            }

                    columns = _resolve_item_columns(value, columns)
                    _process_expanded_item(idx, value, columns)

            if expand_keys and add_index:
                columns = ["Index"] + columns

        elif isinstance(data, Sequence):
            for idx, value in enumerate(data):
                if remove_tabs is not False:
                    value = replace_tabs(value, remove_tabs)
                if not expand_keys:
                    # Whole item is one cell; expanded items are yamlified per field
                    ret.append([idx, yaml_cell(value) if yaml_cells else value])
                else:
                    columns = _resolve_item_columns(value, columns)
                    _process_expanded_item(idx, value, columns)

            if expand_keys and add_index:
                columns = ["Index"] + columns

        else:
            raise ValueError(
                f"Data must be a list of dictionaries or lists, got {type(data)}"
            )

        out = (ret, columns or _default_columns)
        return out
