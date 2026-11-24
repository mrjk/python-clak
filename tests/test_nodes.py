"""Unit tests for the nodes module.

This module contains function-based tests for the core node classes and utilities.
"""

import pytest

from clak.core.nodes import NOT_SET, Node
from clak.exception import ConfigurationError, MissingMetaError

pytestmark = pytest.mark.tags("unit-tests")


# Test empty class helpers
# ==============================


def test_not_set():
    """NOT_SET is a falsy marker distinct from None."""
    assert str(NOT_SET) == "<NOT_SET>"
    assert repr(NOT_SET) == "<NOT_SET>"
    assert bool(NOT_SET) is False
    assert NOT_SET is not None


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
    assert node.query_cfg_inst("direct_value") == "direct_test"

    # Test Meta class access
    assert node.query_cfg_inst("meta_value") == "meta_test"

    # Test meta__ prefix access
    assert node.query_cfg_inst("default_value") == "default_test"

    # Test with default value
    value = node.query_cfg_inst("nonexistent", default="default")
    assert value == "default"

    # Test error case
    with pytest.raises(IndexError):
        node.query_cfg_inst("nonexistent")


def test_node_query_cfg_parents_complex():
    """Test Node query_cfg_parents with complex hierarchy and different value locations."""
    root = Node(name="root")
    root.meta__config__root_val = True
    root._root_val = "root_value"

    mid = Node(name="mid", parent=root)
    mid.meta__config__mid_val = True
    mid._mid_val = "mid_value"

    leaf = Node(name="leaf", parent=mid)
    leaf.meta__config__leaf_val = True
    leaf._leaf_val = "leaf_value"

    # Test value from immediate parent
    value = leaf.query_cfg_parents("mid_val")
    assert value == "mid_value"

    # Test value from root
    value = leaf.query_cfg_parents("root_val")
    assert value == "root_value"

    # Test with include_self=True
    value = leaf.query_cfg_parents("leaf_val", include_self=True, default="not_found")
    assert value == "leaf_value"

    # Test with include_self=False
    with pytest.raises(MissingMetaError):
        leaf.query_cfg_parents("leaf_val", include_self=False, default="not_found")

    # Test with include_self=False and no defaults
    with pytest.raises(MissingMetaError):
        leaf.query_cfg_parents("leaf_val", include_self=False)


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
    root.meta__config__test_value = True
    root._test_value = "root_value"

    child = Node(name="child", parent=root)
    child._child_value = "child_value"

    # Test querying existing value
    value = child.query_cfg_parents("test_value")
    assert value == "root_value"

    # Test with default value
    with pytest.raises(MissingMetaError):
        child.query_cfg_parents("nonexistent")

    # value = child.query_cfg_parents("nonexistent", default="default")
    # assert value == "default"

    # Test without include_self
    value = child.query_cfg_parents("test_value", include_self=False)
    assert value == "root_value"

    # Test raising ConfigurationError
    with pytest.raises(ConfigurationError):
        child.query_cfg_parents("nonexistent")


def test_missing_meta_error_interpolates_node_repr():
    """MissingMetaError must include the node repr, not a literal placeholder."""
    node = Node(name="leaf")
    with pytest.raises(MissingMetaError) as exc:
        node.query_cfg_parents("nope")
    msg = str(exc.value)
    assert "{repr(self)}" not in msg
    assert repr(node) in msg

    with pytest.raises(IndexError) as exc:
        node.query_cfg_inst("nope")
    msg = str(exc.value)
    assert "{repr(self)}" not in msg
    assert repr(node) in msg


def test_query_cfg_parents_reads_undeclaring_child_meta():
    """A child that does not declare a setting may still override its value."""
    root = Node(name="root")
    root.meta__config__color = True
    root._color = "root"

    child = Node(name="child", parent=root)
    child._color = "child"

    assert child.query_cfg_parents("color") == "child"
    assert child.query_cfg_parents("color", include_self=False) == "root"
