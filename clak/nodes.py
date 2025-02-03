"""
Core node classes and utilities for the Clak framework.

This module provides the foundational classes and types used throughout Clak for
building command-line interfaces. It includes special null-type markers for handling
unset values and configuration inheritance.

Key components:
- NullType: Base class for special null-type markers
- NotSet: Marker for unset configuration values 
- UnSetArg: Marker for unset command arguments
- Node: Base class for building hierarchical command structures
- Fn: Function wrapper for command handlers
"""

import copy
import logging
# from pprint import pprint
from types import SimpleNamespace
from typing import Any, List, Tuple, Union

logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods


class NullType:
    """
    A special type that behaves as a replacement for None.
    We have to put a new default value to know if a variable has been set by
    the user explicitly. This is useful for the ``CommandLine`` loader, when
    CLI parsers force you to set a default value, and thus, break the discovery
    chain.

    This is intentionally a simple class with minimal methods as it serves
    as a base for null-type markers.
    """

    def repr(self):
        "Return string representation"
        return "<NONE_TYPE>"

    def __str__(self):
        return self.repr()

    def __repr__(self):
        return self.repr()

    def __bool__(self):
        return False


class NotSet(NullType):
    """Represent an unset arg.

    Simple marker class intentionally containing minimal functionality.
    """

    def repr(self):
        return "<NOT_SET>"


class UnSetArg(NullType):
    """Represent an unset arg.

    Simple marker class intentionally containing minimal functionality.
    """

    def repr(self):
        return "<UNSET_ARG>"


class Failure(NullType):
    """Represent a failure.

    Simple marker class intentionally containing minimal functionality.
    """

    def repr(self):
        return "<FAILURE>"


class Default(NullType):
    """Represent a default.

    Simple marker class intentionally containing minimal functionality.
    """

    def repr(self):
        return "<DEFAULT>"


NOT_SET = NotSet()
UNSET_ARG = UnSetArg()
FAILURE = Failure()
DEFAULT = Default()


class Fn(SimpleNamespace):
    """A simple namespace that keeps in memory its init arguments.

    This class is intentionally minimal as it serves as a function wrapper.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs


class ConfigurationError(Exception):
    """Raised when a configuration setting cannot be found."""


class MissingMetaError(ConfigurationError):
    """Raised when a meta setting is not declared before being used."""


class Node:
    "New version and simpler version of node"

    name: str = None
    parent: "Node" = None

    class Meta:
        """Class to store class-level configuration overrides.

        This is intentionally an empty class used as a configuration container.
        """

    def __init__(self, name=UNSET_ARG, parent=None):

        # Initialize name
        self.name = (
            name if name is not UNSET_ARG else f"{self.__class__.__name__}"
        )  # ({hex(id(self))})"
        assert isinstance(self.name, str)  # To unit test

        # Initialize parent
        self.parent = parent
        assert isinstance(self.parent, (Node, type(None)))  # To unit test

    def get_hierarchy(self):
        "Return the hierarchy of the node"

        hierarchy = []
        current = self
        while current is not None:
            hierarchy.append(current)
            current = current.parent
        hierarchy.reverse()
        return hierarchy

    def get_name(self, attr="name", default=UNSET_ARG):
        "Return the name of the parser"
        if default is not UNSET_ARG:
            return getattr(self, attr, default)
        return getattr(self, attr)

    def get_fname(self, attr="name"):
        "Return the full name of the parser"
        parents = self.get_hierarchy()

        if parents:
            fname = [x.get_name(attr=attr, default=None) or "" for x in parents]
            return ".".join(fname) or ""
        return ""

    def query_cfg_parents(
        self,
        name: str,
        default: Any = UNSET_ARG,
        include_self: bool = True,
        report: bool = False,
    ) -> Union[Any, Tuple[Any, Union[str, List[str]]]]:
        """Query configuration from parent objects in the hierarchy.

        Args:
            name: Configuration setting name to query
            default: Default value if setting is not found
            include_self: Whether to include this node in the search
            report: Whether to return detailed report of the search

        Returns:
            If report=False:
                The configuration value found in the hierarchy or default
            If report=True:
                Tuple of (value, report_str) where report_str contains search details

        Raises:
            ConfigurationError: If no parent exists, include_self=False, and no default provided
        """

        # Fast exit or raise exception
        if not self.parent and include_self is False:
            if default is not UNSET_ARG:
                if report:
                    return default, "No parents, return default value"
                return default
            msg = (
                f"Setting '{name}' has not been declared in hierarchy of '{repr(self)}'"
            )
            raise ConfigurationError(msg)

        # Prepare lookup chain
        _report = []
        parents = self.get_hierarchy()
        if include_self is False:
            parents = parents[:-1]
        parents.reverse()  # Start from self/immediate parent
        out = NOT_SET
        last_checked_parent = None

        declared = False
        for parent in parents:
            last_checked_parent = parent
            _report.append(f"Check '{name}' in parent {parent}")

            # If not found in direct attribute, try query_cfg_inst
            try:
                out, _report2 = parent.query_cfg_inst(
                    name,
                    default=NOT_SET,
                    report=True,
                    raise_on_undeclared=True,
                )
                declared = declared or True
                _report.append(_report2)
                if out is not NOT_SET:
                    _report.append(f"Found '{name}' in parent {parent}= {out}")
                    break
            except MissingMetaError:
                declared = declared or False
                continue
            except IndexError:
                declared = declared or False
                continue

        if not declared:
            msg = f"Missing 'meta__config__{name}', this option has not been declared in any parents of'{repr(self)}'"
            raise MissingMetaError(msg)

        if out is NOT_SET:
            _report.append(f"NotFound '{name}' in parent: {last_checked_parent}")
        if out is NOT_SET and default is not UNSET_ARG:
            out = default
        elif out is NOT_SET:
            msg = (
                f"Setting '{name}' has not been declared in hierarchy of '{repr(self)}'"
            )
            raise ConfigurationError(msg)

        if report:
            return out, _report
        return out

    def query_cfg_inst(
        self,
        name,
        override=None,
        default=UNSET_ARG,
        report=False,
        raise_on_undeclared=False,
    ):
        "Query configuration from instance"

        # if not hasattr(self, f"meta__config__{name}"):
        if raise_on_undeclared and getattr(self, f"meta__config__{name}", None) is None:
            msg = f"Missing 'meta__config__{name}', this option has not been declared '{repr(self)}'"
            raise MissingMetaError(msg)

        def _query():
            "Helper to process query"

            query_from = []

            # Fetch from dict override, if provided
            if isinstance(override, dict):
                val = override.get(name, NOT_SET)
                if val is not NOT_SET:
                    query_from.append(f"dict_override:{name}")
                    return val, query_from

            # Fetch from self._NAME
            # Good for initial setup, if write mode is required
            val = getattr(self, f"_{name}", NOT_SET)
            if val is not NOT_SET:
                query_from.append(f"self_attr:_{name}")
                return val, query_from

            # Python class params
            # Good for class overrides
            cls = self
            if hasattr(cls, "Meta"):
                val = getattr(cls.Meta, name, NOT_SET)
                if val is not NOT_SET:
                    query_from.append(f"self_meta:Meta.{name}")
                    # print ("SELF CLASS Meta retrieval for: {cls}" , name, val)
                    return val, query_from

            # Fetch from self.meta__NAME
            # Python class inherited params (good for defaults)
            val = getattr(self, f"meta__{name}", NOT_SET)
            if val is not NOT_SET:
                query_from.append(f"self_attr:meta__{name}")
                return val, query_from

            # Return default if set
            if default is not UNSET_ARG:
                query_from.append("default_arg")
                return default, query_from

            # Raise error if not found
            msg = (
                f"Setting '{name}' has not been declared before being used"
                f" in '{repr(self)}', tried to query: {query_from}"
            )
            raise IndexError(msg)

        # Return output
        out, _report = _query()

        # Ensure we always deliver copies
        if isinstance(out, (dict, list)):
            out = copy.copy(out)

        if report:
            return out, _report
        return out
