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

import csv
import io
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

from clak.common import replace_tabs
from clak.settings import CLAK_COLORS

OUTPUT_FORMATS = frozenset({"view", "yaml", "json", "csv"})
SORT_MODES = frozenset({"asc", "desc"})


def require_yaml():
    """Import PyYAML or raise a clear InstallError-style ImportError."""
    try:
        import yaml  # pylint: disable=import-outside-toplevel
    except ImportError as err:
        raise ImportError(
            "PyYAML is required for --format yaml. Install with: pip install pyyaml"
        ) from err
    return yaml


# assert False


# pylint: disable=invalid-name
table_kwargs = {}
if not CLAK_COLORS:
    from prettytable import PrettyTable

    table_cls = PrettyTable
else:
    try:
        # Colortable use colorama to colorize text, but the latest patches
        # the stderr/out python commands, and thus add a reset shell code
        # after each line, and thus break regression tests on CLI output.
        from prettytable.colortable import ColorTable, Themes

        table_cls = ColorTable
        table_kwargs = {"theme": Themes.GLARE_REDUCTION}
    except ImportError:
        from prettytable import PrettyTable

        table_cls = PrettyTable


# from pprint import pformat, pprint


################## Parent class


# To create hrule
def create_separator(table):
    "Create a separator line for the table"
    return ["-" * len(str(col)) for col in table.field_names]


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


def resolve_sort_column_index(col, headers):
    """Resolve a sort column to a 0-based index in *headers*.

    - str: header name
    - int < 0: index from end (-1 = last column)
    - int > 0: 1-based index (1 = first column)
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
                "Sort column index 0 is invalid; use 1 for first column or -1 for last"
            )
        if col < 0:
            idx = len(headers) + col
        else:
            idx = col - 1
        if idx < 0 or idx >= len(headers):
            choices = ", ".join(str(header) for header in headers)
            raise KeyError(f"Sort column index {col} out of range, choices: {choices}")
        return idx

    raise TypeError(f"Sort column must be a string or int, got {type(col).__name__}")


def sort_table_rows(rows, headers, sort_columns, sort_mode="asc"):
    """Sort tabular rows by one or more header names or indexes."""
    if not sort_columns or not rows:
        return rows

    reverse = normalize_sort_mode(sort_mode)
    indexes = [resolve_sort_column_index(col, headers) for col in sort_columns]

    def key_fn(row):
        return [str(row[idx]) if idx < len(row) else "" for idx in indexes]

    return sorted(rows, key=key_fn, reverse=reverse)


def default_sort_columns(headers):
    """Default: sort by the first displayed column, ascending."""
    if not headers:
        return None
    return [1]


def format_structured(rows, headers, fmt):
    """Render tabular rows as yaml, json, or csv."""
    if fmt not in OUTPUT_FORMATS - {"view"}:
        raise ValueError(
            f"Unsupported format {fmt!r}, choose one of: {sorted(OUTPUT_FORMATS)}"
        )

    if fmt == "json":
        records = [dict(zip(headers, row)) for row in rows]
        return json.dumps(records, indent=2, default=str) + "\n"

    if fmt == "yaml":
        yaml = require_yaml()
        records = [dict(zip(headers, row)) for row in rows]
        return yaml.safe_dump(records, sort_keys=False, default_flow_style=False)

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        return buf.getvalue()

    raise ValueError(f"Unsupported format {fmt!r}")


class _TableFormatter(ABC):
    "Table view"

    view_options = {
        "columns": None,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
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

    def table_render_show(self, data, **view_options):
        "Create a PrettyTable instance, configure it and print it"

        _view_options = dict(self.view_options)
        _view_options.update(view_options)

        fmt = _view_options.pop("format", "view") or "view"
        sort_columns = _view_options.pop("sort_columns", None)
        sort_mode = _view_options.pop("sort_mode", "asc") or "asc"

        data_table, headers = self.process_table(data, **_view_options)
        self.validate_table_data(data_table)

        if not sort_columns and headers:
            sort_columns = default_sort_columns(headers)

        if sort_columns:
            data_table = sort_table_rows(
                data_table, headers, sort_columns, sort_mode=sort_mode
            )

        if fmt != "view":
            return format_structured(data_table, headers, fmt)

        # Prepare table
        # table = ColorTable(theme=Themes.GLARE_REDUCTION)
        # table = ColorTable(theme=Themes.PASTEL)
        # table = PrettyTable()
        table = table_cls(**table_kwargs)
        table.field_names = headers
        table.align = "l"
        for line in data_table:
            table.add_row(line)

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


class TableShowFormatter(_TableFormatter):
    "Table show item"

    view_options = {
        "add_index": True,
        "columns": None,
        "remove_tabs": True,
        "format": "view",
        "sort_columns": None,
        "sort_mode": "asc",
    }

    def process_table(self, data, columns=None, add_index=True, remove_tabs=True):
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

        assert isinstance(add_index, bool), f"Got: {add_index}"
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
    }

    # pylint: disable=too-many-branches,too-many-arguments,too-many-positional-arguments
    def process_table(
        self, data, columns=None, add_index=None, expand_keys=False, remove_tabs=True
    ):
        "Restructure data to fit to list view"

        add_index = add_index if isinstance(add_index, bool) else not expand_keys

        if not expand_keys and columns is not None:
            raise ValueError(
                f"Cannot specify columns when expand_keys is False: {columns}"
            )

        ret = []

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
                row.append(value)
            ret.append(row)

        _default_columns = ["Key", "Value"]
        if isinstance(data, Mapping):
            for idx, value in data.items():
                if not expand_keys:
                    ret.append([idx, value])
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

                    # Grab columns from 1st item
                    columns = list(value.keys()) if columns is None else columns
                    _process_expanded_item(idx, value, columns)

            if expand_keys and add_index:
                columns = ["Index"] + columns

        elif isinstance(data, Sequence):
            for idx, value in enumerate(data):
                if remove_tabs is not False:
                    value = replace_tabs(value, remove_tabs)
                if not expand_keys:
                    ret.append([idx, value])
                else:

                    # Grab columns from 1st item
                    if isinstance(value, Mapping):
                        columns = list(value.keys()) if columns is None else columns
                    else:
                        columns = (
                            list(range(0, len(value))) if columns is None else columns
                        )
                    _process_expanded_item(idx, value, columns)

            if expand_keys and add_index:
                columns = ["Index"] + columns

        else:
            raise ValueError(
                f"Data must be a list of dictionaries or lists, got {type(data)}"
            )

        out = (ret, columns or _default_columns)
        return out
