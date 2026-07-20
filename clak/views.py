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

import logging
import os
import textwrap
from pprint import pformat

from clak.table_formatter import TableListFormatter, TableShowFormatter

logger = logging.getLogger(__name__)

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
        rendered = TableShowFormatter().render(payload, **settings)
        return self._output(rendered, stdout=stdout)


class ListView(FeatureFullViewier):
    "Render list data"

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        rendered = TableListFormatter().render(payload, **settings)
        return self._output(rendered, stdout=stdout)
