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


def test_node_get_fname():
    """Test Node get_fname method."""
    root = Node(name="root")
    child1 = Node(name="child1", parent=root)
    child2 = Node(name="child2", parent=child1)

    assert root.get_fname() == "root"
    assert child1.get_fname() == "root.child1"
    assert child2.get_fname() == "root.child1.child2"

def test_node_get_fname_empty():
    """Test Node get_fname method with empty root"""
    root = Node(name="")
    child1 = Node(name="child1", parent=root)
    child2 = Node(name="child2", parent=child1)

    assert root.get_fname() == ""
    assert child1.get_fname() == ".child1"
    assert child2.get_fname() == ".child1.child2"


def test_node_get_fname_empty():
    """Test Node get_fname method with empty root"""
    root = Node(name="")
    child1 = Node(name="", parent=root)
    child2 = Node(name="", parent=child1)

    assert root.get_fname() == ""
    assert child1.get_fname() == "."
    assert child2.get_fname() == ".."

def test_node_get_fname_empty():
    """Test Node get_fname method with unset names"""
    root = Node()
    child1 = Node(parent=root)
    child2 = Node(parent=child1)

    assert root.get_fname() == "Node"
    assert child1.get_fname() == "Node.Node"
    assert child2.get_fname() == "Node.Node.Node"



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