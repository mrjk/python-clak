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

# from pprint import pprint, pformat
from collections.abc import Mapping, Sequence

from prettytable import PrettyTable

################## Parent class


class _TableFormatter(ABC):
    "Table view"

    view_options = {
        "columns": None,
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

        try:
            data_table, headers = self.process_table(data, **_view_options)
            self.validate_table_data(data_table)
        except TypeError as err:
            choices = ", ".join(self.view_options.keys())
            msg = f"{err}, please choose one of: {choices}"
            raise TypeError(msg) from None

        # Prepare table
        table = PrettyTable()
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
    }

    def process_table(self, data, columns=None, add_index=True):
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
            except KeyError:
                choices = ",".join(choices)
                raise KeyError(
                    f"Key {key} not found in data, choices: {choices}"
                ) from None

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
    }

    # pylint: disable=too-many-branches
    def process_table(self, data, columns=None, add_index=None, expand_keys=False):
        "Restructure data to fit to item view"

        add_index = add_index if isinstance(add_index, bool) else not expand_keys

        if not expand_keys and columns is not None:
            raise ValueError(
                f"Cannot specify columns when expand_keys is False: {columns}"
            )

        ret = []

        def _process_expanded_item(idx, item, columns):
            _out = []
            if add_index:
                _out = [idx]

            for field in columns:
                _out.append(item[field])
            ret.append(_out)

        _default_columns = ["Key", "Value"]
        if isinstance(data, Mapping):
            for idx, value in data.items():
                if not expand_keys:
                    ret.append([idx, value])
                else:
                    # Grab columns from 1st item
                    columns = list(value.keys()) if columns is None else columns
                    _process_expanded_item(idx, value, columns)

            if expand_keys and add_index:
                columns = ["Index"] + columns

        elif isinstance(data, Sequence):
            for idx, value in enumerate(data):
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
