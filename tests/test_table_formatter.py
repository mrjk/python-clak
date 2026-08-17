"""
Test functions for table formatter classes.
"""

from pprint import pprint

import pytest

from clak.views.table_formatter import (
    TableListFormatter,
    TableShowFormatter,
    resolve_column_index,
    resolve_column_keys,
    resolve_sort_column_index,
)

pytestmark = pytest.mark.tags("unit-tests")

################## Test data

# For test 1
data_item_dict1 = {
    "name": "World",
    "age": 42,
    "city": "Paris",
}

data_item_list1 = [
    "World",
    42,
    "Cergy",
]

# For test 2
data_item_dict2 = {
    "name": "Neptune",
    "age": 43,
    "city": "Nantes",
}

data_item_list2 = [
    "Mars",
    43,
    "Brussels",
]

data_items_dict = {
    "item1": data_item_dict1,
    "item2": data_item_dict2,
}

data_items_list = [
    data_item_list1,
    data_item_list2,
]


################## Test TableShowFormatter


def test_show_dict_default():
    """Test TableShowFormatter with default settings on dictionary"""
    output = TableShowFormatter().render(data_item_dict1)
    assert "World" in output
    assert "Paris" in output
    assert "Key" in output  # Should have Key column
    assert "Value" in output  # Should have Value column


def test_show_formatter_ignores_unknown_kwargs():
    output = TableShowFormatter().render(data_item_dict1, expand_keys=True)
    assert "World" in output
    assert "Key" in output


def test_show_dict_no_index():
    """Test TableShowFormatter without index on dictionary"""
    output = TableShowFormatter(add_index=False).render(data_item_dict1)
    assert "World" in output
    assert "Paris" in output
    assert "Key" not in output  # Should not have Key column
    assert "Value" in output  # Should have Value column


def test_show_dict_with_columns():
    """Test TableShowFormatter with specific columns on dictionary"""
    output = TableShowFormatter().render(data_item_dict1, columns=["name", "age"])
    pprint(data_item_dict1)
    print(output)
    assert "World" in output
    assert "42" in output
    assert "Paris" not in output  # Should not include city
    assert "Key" in output
    assert "Value" in output


def test_show_list_default():
    """Test TableShowFormatter with default settings on list"""
    output = TableShowFormatter().render(data_item_list1)
    assert "World" in output
    assert "42" in output
    assert "Index" in output  # Should have Index column
    assert "Value" in output


def test_show_list_no_index():
    """Test TableShowFormatter without index on list"""
    output = TableShowFormatter(add_index=False).render(data_item_list1)
    assert "World" in output
    assert "42" in output
    assert "Index" not in output
    assert "Value" in output


from pprint import pprint


def test_show_list_with_columns_with_indexes():
    """Test TableShowFormatter with specific columns on list"""
    output = TableShowFormatter().render(
        data_item_list1, columns=[1, 3], add_index=True
    )
    pprint(data_item_list1)
    print(output)
    assert "World" in output
    assert "Cergy" in output
    assert "42" not in output  # Should not include middle element
    assert "Index" in output
    assert "Value" in output


def test_show_list_with_columns_without_indexes():
    """Test TableShowFormatter with specific columns on list"""
    output = TableShowFormatter().render(
        data_item_list1, columns=[1, 3], add_index=False
    )
    pprint(data_item_list1)
    print(output)
    assert "World" in output
    assert "Cergy" in output
    assert "42" not in output  # Should not include middle element
    assert "Index" not in output
    assert "Value" in output


################## Test TableListFormatter

# Matrix test parameters
test_data = [
    ("dict", data_items_dict, ["name", "age"], ["World", "Neptune"]),
    ("list", data_items_list, [1, 3], ["World", "Mars"]),
]


@pytest.mark.parametrize("data_type,data,columns,expected_values", test_data)
def test_list_expand_matrix(data_type, data, columns, expected_values):
    """Matrix test for TableListFormatter with various combinations"""

    # Test without expand (should fail with columns)
    with pytest.raises(ValueError):
        TableListFormatter(data, expand_keys=False, columns=columns).render(data)

    # Test with expand and columns
    output = TableListFormatter(data, expand_keys=True, columns=columns).render(data)
    for value in expected_values:
        assert value in output

    # Test with expand, columns and index
    output = TableListFormatter(
        data, expand_keys=True, add_index=True, columns=columns
    ).render(data)
    assert "Index" in output
    for value in expected_values:
        assert value in output

    # Test with expand, columns but no index
    output = TableListFormatter(
        data, expand_keys=True, add_index=False, columns=columns
    ).render(data)
    assert "Index" not in output
    for value in expected_values:
        assert value in output


def test_list_dict_no_expand():
    """Test TableListFormatter with dictionary without expand"""
    output = TableListFormatter(data_items_dict, expand_keys=False).render(
        data_items_dict
    )
    assert "item1" in output
    assert "item2" in output
    assert isinstance(output, str)  # Should return a string
    assert "Key" in output
    assert "Value" in output


def test_list_list_no_expand():
    """Test TableListFormatter with list without expand"""
    output = TableListFormatter(data_items_list, expand_keys=False).render(
        data_items_list
    )
    assert isinstance(output, str)  # Should return a string
    assert "Key" in output
    assert "Value" in output


def test_list_invalid_data():
    """Test TableListFormatter with invalid data type"""
    invalid_data = "not a list or dict"
    with pytest.raises(ValueError) as exc_info:
        TableListFormatter().render(invalid_data)
    assert "Data must be a list or dict," in str(exc_info.value)


def test_list_dict_expand_default_columns():
    """Test TableListFormatter with dictionary and expanded keys using default columns"""
    output = TableListFormatter(data_items_dict, expand_keys=True).render(
        data_items_dict
    )
    # Should include all fields since no columns specified
    assert "name" in output
    assert "age" in output
    assert "city" in output
    assert "World" in output
    assert "Neptune" in output
    assert "Paris" in output
    assert "Nantes" in output


def test_list_list_expand_default_columns():
    """Test TableListFormatter with list and expanded keys using default columns"""
    output = TableListFormatter(data_items_list, expand_keys=True).render(
        data_items_list
    )
    # Should include all indices since no columns specified
    assert "World" in output
    assert "Mars" in output
    assert "42" in output
    assert "43" in output
    assert "Cergy" in output
    assert "Brussels" in output


@pytest.mark.parametrize("add_index", [True, False])
def test_list_expand_index_behavior(add_index):
    """Test TableListFormatter index behavior with expanded keys"""
    # Test with dict
    output_dict = TableListFormatter(
        data_items_dict, expand_keys=True, add_index=add_index
    ).render(data_items_dict)

    assert ("Index" in output_dict) == add_index

    # Test with list
    output_list = TableListFormatter(
        data_items_list, expand_keys=True, add_index=add_index
    ).render(data_items_list)

    assert ("Index" in output_list) == add_index


def test_list_expand_heterogeneous_dicts_uses_placeholder():
    data = [{"name": "World"}, {"age": 42}]

    output = TableListFormatter().render(
        data,
        columns=["name", "age"],
        expand_keys=True,
        add_index=True,
    )

    assert "World" in output
    assert "42" in output
    assert "-" in output


def test_render_stdout_still_returns_output(capsys):
    output = TableShowFormatter().render(data_item_dict1, stdout=True)

    assert isinstance(output, str)
    assert output in capsys.readouterr().out


def test_resolve_sort_column_index_negative_and_one_based():
    headers = ["name", "role", "city"]

    assert resolve_sort_column_index(-1, headers) == 2
    assert resolve_sort_column_index(-3, headers) == 0
    assert resolve_sort_column_index(1, headers) == 0
    assert resolve_sort_column_index(2, headers) == 1
    assert resolve_sort_column_index("role", headers) == 1


def test_resolve_column_index_rejects_zero():
    headers = ["name", "role", "city"]

    with pytest.raises(KeyError, match="index 0 is invalid"):
        resolve_column_index(0, headers)


def test_resolve_column_keys_one_based_and_names():
    headers = ["name", "role", "city"]

    assert resolve_column_keys([1, -1], headers) == ["name", "city"]
    assert resolve_column_keys(["role", 3], headers) == ["role", "city"]


def test_list_formatter_default_sorts_first_column():
    data = [
        {"name": "linus", "role": "dev"},
        {"name": "ada", "role": "admin"},
    ]

    output = TableListFormatter().render(data, expand_keys=True)

    assert output.index("ada") < output.index("linus")


def _plain_table(output: str) -> str:
    """Strip ANSI color codes from ColorTable output."""
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", output)


def test_table_width_min_keeps_content_size():
    long_val = "x" * 60
    data = [{"name": "a", "note": long_val}]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="min",
            term_width=40,
            stdout_tty=True,
        )
    )
    lines = [line for line in output.splitlines() if line.startswith("+")]
    assert lines
    assert len(lines[0]) > 40


def test_table_width_auto_wraps_when_wider_than_terminal():
    long_val = "word " * 20
    data = [{"name": "a", "note": long_val}]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            term_width=40,
            stdout_tty=True,
        )
    )
    lines = output.splitlines()
    assert max(len(line) for line in lines) <= 41


def test_table_width_terminal_uses_full_term_width():
    data = [{"name": "a", "note": "hi"}]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="terminal",
            term_width=50,
            stdout_tty=True,
        )
    )
    border = next(line for line in output.splitlines() if line.startswith("+"))
    assert len(border) == 50


def test_table_width_no_wrap_when_not_tty():
    long_val = "x" * 60
    data = [{"name": "a", "note": long_val}]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="terminal",
            term_width=40,
            stdout_tty=False,
        )
    )
    lines = [line for line in output.splitlines() if line.startswith("+")]
    assert lines
    assert len(lines[0]) > 40


_LONG_NOTE = "127.0.0.1:80->80/tcp, 127.0.0.1:443->443/tcp, " "127.0.0.1:8080->8080/tcp"


def _first_border(output: str) -> str:
    return next(line for line in output.splitlines() if line.startswith("+"))


def _render_list_table(data, **kwargs):
    return _plain_table(TableListFormatter().render(data, expand_keys=True, **kwargs))


def test_table_width_terminal_wraps_long_last_cell_to_term_width():
    data = [{"name": "web", "note": _LONG_NOTE}]
    output = _render_list_table(
        data,
        width="terminal",
        wrap="last",
        term_width=80,
        stdout_tty=True,
    )
    assert len(_first_border(output)) == 80
    header = next(line for line in output.splitlines() if "name" in line)
    assert "| name " in header or "| name |" in header


def test_table_width_terminal_pads_long_last_cell_when_it_fits():
    data = [{"name": "web", "note": _LONG_NOTE}]
    term_width = 200
    output = _render_list_table(
        data,
        width="terminal",
        wrap="last",
        term_width=term_width,
        stdout_tty=True,
    )
    assert len(_first_border(output)) == term_width
    content = _render_list_table(
        data,
        width="content",
        wrap="last",
        term_width=term_width,
        stdout_tty=True,
    )
    assert len(_first_border(content)) < term_width


def test_table_width_fit_does_not_stretch_when_narrower_than_tty():
    data = [{"name": "a", "note": "hi"}]
    fit = _render_list_table(
        data,
        width="fit",
        wrap="last",
        term_width=80,
        stdout_tty=True,
    )
    content = _render_list_table(
        data,
        width="content",
        wrap="last",
        term_width=80,
        stdout_tty=True,
    )
    fit_border = len(_first_border(fit))
    assert fit_border == len(_first_border(content))
    assert fit_border < 80


def test_table_width_terminal_long_cell_honors_term_width_with_colors():
    from clak.views.table_formatter import table_cls

    if table_cls.__name__ != "ColorTable":
        pytest.skip("ColorTable not active (CLAK_COLORS off)")
    data = [{"name": "web", "note": _LONG_NOTE}]
    output = _render_list_table(
        data,
        width="terminal",
        wrap="last",
        term_width=80,
        stdout_tty=True,
    )
    assert len(_first_border(output)) == 80


def test_table_wrap_last_keeps_left_columns():
    data = [
        {
            "name": "ada",
            "role": "admin",
            "note": "word " * 20,
        }
    ]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            wrap="last",
            term_width=50,
            stdout_tty=True,
        )
    )
    header = next(line for line in output.splitlines() if "name" in line)
    assert "name" in header
    assert "role" in header
    # Left headers should not be truncated like "na" / "ro"
    assert "| name " in header or "| name |" in header
    assert "| role " in header or "| role |" in header
    assert max(len(line) for line in output.splitlines()) <= 51


def test_table_wrap_all_may_shrink_left_columns():
    data = [
        {
            "name": "ada",
            "role": "admin",
            "note": "word " * 20,
        }
    ]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            wrap="all",
            term_width=50,
            stdout_tty=True,
        )
    )
    header = next(line for line in output.splitlines() if "n" in line.lower())
    # PrettyTable max_table_width may shrink left headers
    assert max(len(line) for line in output.splitlines()) <= 51
    assert "note" in header or "no" in header


def _border_segments(output: str):
    border = next(line for line in output.splitlines() if line.startswith("+"))
    return [len(part) for part in border.strip("+").split("+")]


def _wrap_data(first="ada", middle="admin", last=None):
    return [
        {
            "name": first,
            "role": middle,
            "note": last if last is not None else "word " * 20,
        }
    ]


def test_table_wrap_first_keeps_right_columns():
    data = [{"note": "word " * 20, "name": "ada", "role": "admin"}]
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            wrap="first",
            term_width=50,
            stdout_tty=True,
        )
    )
    header = next(line for line in output.splitlines() if "name" in line)
    assert "| name " in header or "| name |" in header
    assert "| role " in header or "| role |" in header
    assert max(len(line) for line in output.splitlines()) <= 51


def test_table_wrap_named_column_keeps_neighbors():
    output = _plain_table(
        TableListFormatter().render(
            _wrap_data(),
            expand_keys=True,
            width="auto",
            wrap="note",
            term_width=50,
            stdout_tty=True,
        )
    )
    header = next(line for line in output.splitlines() if "name" in line)
    assert "| name " in header or "| name |" in header
    assert "| role " in header or "| role |" in header
    assert max(len(line) for line in output.splitlines()) <= 51


def test_table_wrap_negative_index_equals_last():
    kwargs = dict(
        expand_keys=True,
        width="auto",
        term_width=50,
        stdout_tty=True,
    )
    last = _plain_table(
        TableListFormatter().render(_wrap_data(), wrap="last", **kwargs)
    )
    by_index = _plain_table(
        TableListFormatter().render(_wrap_data(), wrap=-1, **kwargs)
    )
    assert last == by_index


def test_table_wrap_priority_shrinks_first_listed_before_second():
    data = _wrap_data(first="abcdefghijklmnop", last="x" * 80)
    natural = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="content",
            stdout_tty=True,
        )
    )
    nat_segs = _border_segments(natural)
    overflow = 20
    term_width = len(natural.splitlines()[0]) - overflow
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            wrap=["note", "name"],
            term_width=term_width,
            stdout_tty=True,
        )
    )
    segs = _border_segments(output)
    assert segs[0] == nat_segs[0]
    assert segs[1] == nat_segs[1]
    assert segs[2] < nat_segs[2]
    assert max(len(line) for line in output.splitlines()) <= term_width + 1


def test_table_wrap_min_stops_first_column_then_shrinks_next():
    data = _wrap_data(first="abcdefghijklmnop", last="x" * 80)
    natural = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="content",
            stdout_tty=True,
        )
    )
    nat_segs = _border_segments(natural)
    note_content = nat_segs[2] - 2
    wrap_min_note = 30
    overflow = (note_content - wrap_min_note) + 10
    term_width = len(natural.splitlines()[0]) - overflow
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            wrap=["note", "name"],
            wrap_min={"note": wrap_min_note},
            term_width=term_width,
            stdout_tty=True,
        )
    )
    segs = _border_segments(output)
    assert segs[2] - 2 >= wrap_min_note
    assert segs[0] < nat_segs[0]
    assert segs[1] == nat_segs[1]


def test_table_wrap_min_dump_can_go_below_min_on_tiny_terminal():
    data = _wrap_data(last="x" * 80)
    output = _plain_table(
        TableListFormatter().render(
            data,
            expand_keys=True,
            width="auto",
            wrap="note",
            wrap_min={"note": 40},
            term_width=25,
            stdout_tty=True,
        )
    )
    segs = _border_segments(output)
    assert segs[2] - 2 < 40
    assert max(len(line) for line in output.splitlines()) <= 26


def test_table_wrap_unknown_column_raises():
    with pytest.raises(KeyError, match="nope"):
        TableListFormatter().render(
            _wrap_data(),
            expand_keys=True,
            width="auto",
            wrap="nope",
            term_width=50,
            stdout_tty=True,
        )


def test_table_wrap_min_unknown_column_raises():
    with pytest.raises(KeyError, match="nope"):
        TableListFormatter().render(
            _wrap_data(),
            expand_keys=True,
            width="auto",
            wrap="note",
            wrap_min={"nope": 10},
            term_width=50,
            stdout_tty=True,
        )
