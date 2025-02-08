"""
Test functions for table formatter classes.
"""
from pprint import pprint

import pytest

from clak.table_formatter import TableListFormatter, TableShowFormatter

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
    output = TableShowFormatter().render(data_item_list1, columns=[0, 2], add_index=True)
    pprint(data_item_list1)
    print(output)
    assert "World" in output
    assert "Cergy" in output
    assert "42" not in output  # Should not include middle element
    assert "Index" in output
    assert "Value" in output

def test_show_list_with_columns_without_indexes():
    """Test TableShowFormatter with specific columns on list"""
    output = TableShowFormatter().render(data_item_list1, columns=[0, 2], add_index=False)
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
    ('dict', data_items_dict, ["name", "age"], ["World", "Neptune"]),
    ('list', data_items_list, [0, 2], ["World", "Mars"]),
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
    output = TableListFormatter(data, expand_keys=True, add_index=True, columns=columns).render(data)
    assert "Index" in output
    for value in expected_values:
        assert value in output
    
    # Test with expand, columns but no index
    output = TableListFormatter(data, expand_keys=True, add_index=False, columns=columns).render(data)
    assert "Index" not in output
    for value in expected_values:
        assert value in output


def test_list_dict_no_expand():
    """Test TableListFormatter with dictionary without expand"""
    output = TableListFormatter(data_items_dict, expand_keys=False).render(data_items_dict)
    assert "item1" in output
    assert "item2" in output
    assert isinstance(output, str)  # Should return a string
    assert "Key" in output
    assert "Value" in output


def test_list_list_no_expand():
    """Test TableListFormatter with list without expand"""
    output = TableListFormatter(data_items_list, expand_keys=False).render(data_items_list)
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
    output = TableListFormatter(data_items_dict, expand_keys=True).render(data_items_dict)
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
    output = TableListFormatter(data_items_list, expand_keys=True).render(data_items_list)
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
        data_items_dict, 
        expand_keys=True, 
        add_index=add_index
    ).render(data_items_dict)
    
    assert ("Index" in output_dict) == add_index
    
    # Test with list
    output_list = TableListFormatter(
        data_items_list, 
        expand_keys=True, 
        add_index=add_index
    ).render(data_items_list)
    
    assert ("Index" in output_list) == add_index
