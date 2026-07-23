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

# pylint: disable=too-few-public-methods

import json
import logging
import os
import textwrap
from collections.abc import Mapping, Sequence
from pprint import pformat

from clak.table_formatter import (
    TableListFormatter,
    TableShowFormatter,
    format_structured,
)

logger = logging.getLogger(__name__)

OUTPUT_FORMATS = frozenset({"view", "yaml", "json", "csv"})

# MAX_WIDTH = 120
MAX_WIDTH = 80
try:
    CURR_WIDTH = os.get_terminal_size().columns
    MAX_WIDTH = MAX_WIDTH if CURR_WIDTH > MAX_WIDTH else CURR_WIDTH
except OSError:
    CURR_WIDTH = MAX_WIDTH


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
    """Parse a comma-separated --columns value into a list of keys/indexes."""
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
    """Normalize Meta.view_sort_columns (string or sequence) for render settings."""
    if value is None:
        return None
    if isinstance(value, str):
        return parse_sort_columns(value)
    if isinstance(value, (list, tuple)):
        return list(value)
    raise TypeError(
        "view_sort_columns must be a string or sequence, " f"got {type(value).__name__}"
    )


def _project_item_columns(item, columns):
    """Keep original values while projecting selected columns on one row."""
    if isinstance(item, Mapping):
        return {key: item[key] for key in columns if key in item}
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        return [
            item[key] for key in columns if isinstance(key, int) and key < len(item)
        ]
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
        try:
            import yaml
        except ImportError as err:
            raise ImportError(
                "PyYAML is required for --format yaml. Install with: pip install pyyaml"
            ) from err
        return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)

    raise ValueError(f"Unsupported format {fmt!r}")


def format_show_payload(payload, fmt, columns=None):
    """Render a single show payload as yaml, json, or csv."""
    if fmt not in OUTPUT_FORMATS - {"view"}:
        raise ValueError(
            f"Unsupported format {fmt!r}, choose one of: {sorted(OUTPUT_FORMATS)}"
        )

    if fmt in {"json", "yaml"}:
        if columns is not None:
            payload = _project_item_columns(payload, columns)
        return _dump_structured_payload(payload, fmt)

    if fmt == "csv":
        rows, headers = TableShowFormatter().process_table(payload, columns=columns)
        return format_structured(rows, headers, "csv")

    raise ValueError(f"Unsupported format {fmt!r}")


def format_list_payload(payload, fmt, columns=None):
    """Render a list payload as yaml or json with original values.

    Unlike the table path, this does not fill missing cells with ``"-"``,
    strip tabs, add Index columns, or otherwise adapt values for display.
    """
    if fmt not in {"json", "yaml"}:
        raise ValueError(f"Unsupported format {fmt!r}, choose one of: ['json', 'yaml']")

    return _dump_structured_payload(_project_list_columns(payload, columns), fmt)


def pformat_truncated(data, width=MAX_WIDTH):
    "Truncate a text to max lenght and replace by txt"
    data = pformat(data, width=width)

    # Wrap text to max width
    wrapped = textwrap.fill(data, width=width)
    return wrapped


# Helpers views
# ===================================


class PprintView(ClakView):
    "Render list data"

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        rendered = pformat_truncated(payload, **settings)
        return self._output(rendered, stdout=stdout)


# Generic views
# ===================================


class FeatureFullViewier(ClakView):
    "Render command line output"

    settings_default = {
        "columns": None,
    }


class ShowView(FeatureFullViewier):
    "Render show data"

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        fmt = settings.pop("format", None) or "view"
        if fmt != "view":
            rendered = format_show_payload(
                payload,
                fmt,
                columns=settings.get("columns"),
            )
            return self._output(rendered, stdout=stdout)

        rendered = TableShowFormatter().render(payload, **settings)
        return self._output(rendered, stdout=stdout)


class ListView(FeatureFullViewier):
    "Render list data"

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        fmt = settings.pop("format", None) or "view"
        if fmt in {"yaml", "json"}:
            rendered = format_list_payload(
                payload,
                fmt,
                columns=settings.get("columns"),
            )
            return self._output(rendered, stdout=stdout)

        rendered = TableListFormatter().render(payload, format=fmt, **settings)
        return self._output(rendered, stdout=stdout)
