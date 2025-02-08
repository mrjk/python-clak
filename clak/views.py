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

import os
import textwrap
from pprint import pformat

from clak.table_formatter import TableListFormatter, TableShowFormatter

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

    def render(self, *args, **kwargs):
        "Render data"

        payload, _ = self._render(*args, **kwargs)
        return pformat_truncated(payload)


# Generic views
# ===================================


class FeatureFullViewier(ClakView):
    "Render command line output"

    settings_default = {
        "headers": None,
        "fields": None,
    }


class ShowView(FeatureFullViewier):
    "Render show data"

    def render(self, *args, **kwargs):
        "Render data"

        payload, _settings = self._render(*args, **kwargs)
        return TableShowFormatter(payload)


class ListView(FeatureFullViewier):
    "Render list data"

    def render(self, *args, **kwargs):
        "Render data"

        payload_sequence, _settings = self._render(*args, **kwargs)
        return TableListFormatter(payload_sequence)
