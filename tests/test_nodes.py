"""Unit tests for the nodes module.

This module contains function-based tests for the core node classes and utilities.
"""

import pytest
from clak.nodes import (
    NullType,
    NotSet,
    UnSetArg,
    Failure,
    Default,
    NOT_SET,
    UNSET_ARG,
    FAILURE,
    DEFAULT,
    Fn,
    Node,
    ConfigurationError,
)


pytestmark = pytest.mark.tags("unit-tests")


# Test empty class helpers
# ==============================


def test_null_type_base():
    """Test the base NullType class behavior."""
    null = NullType()
    assert str(null) == "<NONE_TYPE>"
    assert repr(null) == "<NONE_TYPE>"
    assert bool(null) is False


def test_not_set():
    """Test NotSet class behavior."""
    not_set = NotSet()
    assert str(not_set) == "<NOT_SET>"
    assert repr(not_set) == "<NOT_SET>"
    assert bool(not_set) is False
    assert NOT_SET is not None


def test_unset_arg():
    """Test UnSetArg class behavior."""
    unset_arg = UnSetArg()
    assert str(unset_arg) == "<UNSET_ARG>"
    assert repr(unset_arg) == "<UNSET_ARG>"
    assert bool(unset_arg) is False
    assert UNSET_ARG is not None


def test_failure():
    """Test Failure class behavior."""
    failure = Failure()
    assert str(failure) == "<FAILURE>"
    assert repr(failure) == "<FAILURE>"
    assert bool(failure) is False
    assert FAILURE is not None


def test_default():
    """Test Default class behavior."""
    default = Default()
    assert str(default) == "<DEFAULT>"
    assert repr(default) == "<DEFAULT>"
    assert bool(default) is False
    assert DEFAULT is not None


def test_fn_initialization():
    """Test Fn class initialization and storage of arguments."""
    args = (1, 2, 3)
    kwargs = {"a": 1, "b": 2}
    fn = Fn(*args, **kwargs)
    
    assert fn.args == args
    assert fn.kwargs == kwargs


# Test nodes
# ==============================

def test_node_initialization():
    """Test Node initialization with different parameters."""
    # Test default initialization
    node = Node()
    assert node.name == "Node"
    assert node.parent is None

    # Test with custom name
    node = Node(name="custom")
    assert node.name == "custom"
    assert node.parent is None

    # Test with parent
    parent = Node(name="parent")
    child = Node(name="child", parent=parent)
    assert child.name == "child"
    assert child.parent is parent


def test_node_hierarchy():
    """Test Node hierarchy functionality."""
    root = Node(name="root")
    child1 = Node(name="child1", parent=root)
    child2 = Node(name="child2", parent=child1)

    hierarchy = child2.get_hierarchy()
    assert len(hierarchy) == 3
    assert hierarchy[0] is root
    assert hierarchy[1] is child1
    assert hierarchy[2] is child2


def test_node_get_name():
    """Test Node get_name method."""
    node = Node(name="test")
    assert node.get_name() == "test"
    assert node.get_name(default="default") == "test"
    assert node.get_name(attr="nonexistent", default="default") == "default"


def test_node_get_fname_basic():
    """Test Node get_fname method with basic hierarchy."""
    root = Node(name="root")
    child1 = Node(name="child1", parent=root)
    child2 = Node(name="child2", parent=child1)

    assert root.get_fname() == "root"
    assert child1.get_fname() == "root.child1"
    assert child2.get_fname() == "root.child1.child2"

def test_node_get_fname_with_empty_root():
    """Test Node get_fname method with empty root name."""
    root = Node(name="")
    child1 = Node(name="child1", parent=root)
    child2 = Node(name="child2", parent=child1)

    assert root.get_fname() == ""
    assert child1.get_fname() == ".child1"
    assert child2.get_fname() == ".child1.child2"


def test_node_get_fname_empty_string():
    """Test Node get_fname method with empty root"""
    root = Node(name="")
    child1 = Node(name="", parent=root)
    child2 = Node(name="", parent=child1)

    assert root.get_fname() == ""
    assert child1.get_fname() == "."
    assert child2.get_fname() == ".."

def test_node_get_fname_empty_unset():
    """Test Node get_fname method with unset names"""
    root = Node()
    child1 = Node(parent=root)
    child2 = Node(parent=child1)

    assert root.get_fname() == "Node"
    assert child1.get_fname() == "Node.Node"
    assert child2.get_fname() == "Node.Node.Node"

def test_node_query_cfg_inst():
    """Test Node query_cfg_inst method."""
    class CustomNode(Node):
        class Meta:
            meta_value = "meta_test"
        meta__default_value = "default_test"

    node = CustomNode(name="test")
    node._direct_value = "direct_test"

    # Test direct attribute access
    value, report = node.query_cfg_inst("direct_value", report=True)
    assert value == "direct_test"
    assert "self_attr:_direct_value" in report[0]

    # Test Meta class access
    value, report = node.query_cfg_inst("meta_value", report=True)
    assert value == "meta_test"
    assert "self_meta:Meta.meta_value" in report[0]

    # Test meta__ prefix access
    value, report = node.query_cfg_inst("default_value", report=True)
    assert value == "default_test"
    assert "self_attr:meta__default_value" in report[0]

    # Test with override
    value = node.query_cfg_inst("test_key", override={"test_key": "override_value"})
    assert value == "override_value"

    # Test with default value
    value = node.query_cfg_inst("nonexistent", default="default")
    assert value == "default"

    # Test error case
    with pytest.raises(IndexError):
        node.query_cfg_inst("nonexistent")

def test_node_query_cfg_parents_complex():
    """Test Node query_cfg_parents with complex hierarchy and different value locations."""
    root = Node(name="root")
    root._root_val = "root_value"
    
    mid = Node(name="mid", parent=root)
    mid._mid_val = "mid_value"
    
    leaf = Node(name="leaf", parent=mid)
    leaf._leaf_val = "leaf_value"

    # Test value from immediate parent
    value = leaf.query_cfg_parents("mid_val")
    assert value == "mid_value"

    # Test value from root
    value = leaf.query_cfg_parents("root_val")
    assert value == "root_value"

    # Test with include_self=False
    value = leaf.query_cfg_parents("leaf_val", include_self=False, default="not_found")
    assert value == "not_found"

    # Test detailed report
    value, report = leaf.query_cfg_parents("root_val", report=True)
    assert value == "root_value"
    assert isinstance(report, list)
    assert any("Found" in r for r in report)

def test_node_deep_copy_behavior():
    """Test that query_cfg_inst returns deep copies of mutable objects."""
    node = Node(name="test")
    node._list_value = [1, 2, 3]
    node._dict_value = {"a": 1, "b": 2}

    # Test list copy
    result = node.query_cfg_inst("list_value")
    assert result == [1, 2, 3]
    assert result is not node._list_value  # Should be a new object

    # Test dict copy
    result = node.query_cfg_inst("dict_value")
    assert result == {"a": 1, "b": 2}
    assert result is not node._dict_value  # Should be a new object

def test_node_query_cfg_parents():
    """Test Node query_cfg_parents method."""
    root = Node(name="root")
    root._test_value = "root_value"
    
    child = Node(name="child", parent=root)
    child._child_value = "child_value"

    # Test querying existing value
    value = child.query_cfg_parents("test_value")
    assert value == "root_value"

    # Test with default value
    value = child.query_cfg_parents("nonexistent", default="default")
    assert value == "default"

    # Test without include_self
    value = child.query_cfg_parents("test_value", include_self=False)
    assert value == "root_value"

    # Test with report
    value, report = child.query_cfg_parents("test_value", report=True)
    assert value == "root_value"
    assert isinstance(report, list)

    # Test raising ConfigurationError
    with pytest.raises(ConfigurationError):
        child.query_cfg_parents("nonexistent") 