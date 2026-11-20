"""Node tree and ``Meta`` configuration lookup (base of ParserNode).

A setting ``<name>`` is declared with ``meta__config__<name>`` and read, in
order, from ``self._<name>``, ``self.Meta.<name>`` then ``self.meta__<name>``.
"""

import copy
from typing import Any

from clak.exception import ConfigurationError, MissingMetaError

__all__ = ["NOT_SET", "Node"]


class _NotSet:
    """Falsy marker for "no value", distinct from ``None``."""

    __slots__ = ()

    def __repr__(self):
        return "<NOT_SET>"

    __str__ = __repr__

    def __bool__(self):
        return False


NOT_SET = _NotSet()
_REQUIRED = object()  # "no default given": raise instead of returning one


class Node:
    "A named node in a parent/children tree with Meta settings lookup"

    name: str = None
    parent: "Node" = None

    class Meta:  # pylint: disable=too-few-public-methods
        """Class-level configuration overrides (empty container)."""

    def __init__(self, name=None, parent=None):
        self.name = self.__class__.__name__ if name is None else name
        if not isinstance(self.name, str):
            raise TypeError(f"Node name must be a str, got {type(self.name).__name__}")

        self.parent = parent
        if not isinstance(self.parent, (Node, type(None))):
            raise TypeError(
                f"Node parent must be a Node or None, got {type(self.parent).__name__}"
            )

    def get_hierarchy(self):
        "Return the nodes from the root down to self"
        hierarchy = []
        current = self
        while current is not None:
            hierarchy.append(current)
            current = current.parent
        hierarchy.reverse()
        return hierarchy

    def get_fname(self, attr="name"):
        "Return the dotted full name of the node (from ``attr`` of each node)"
        return ".".join(getattr(x, attr, None) or "" for x in self.get_hierarchy())

    def query_cfg_parents(
        self, name: str, default: Any = _REQUIRED, include_self: bool = True
    ) -> Any:
        """Query a setting from this node (or its parent) up to the root.

        The setting must be declared (``meta__config__<name>``) on at least
        one node of the lookup chain; values are then read from every node,
        closest first, so a plain subcommand's ``Meta`` overrides a setting
        declared by a mixin on an ancestor.

        Raises:
            MissingMetaError: The setting is not declared in the lookup chain
            ConfigurationError: No value found and no default provided
        """
        chain = self.get_hierarchy()
        if not include_self:
            chain = chain[:-1]
        chain.reverse()

        not_found = f"Setting '{name}' has not been declared in hierarchy of '{self!r}'"
        if not chain:
            if default is not _REQUIRED:
                return default
            raise ConfigurationError(not_found)

        declare_attr = f"meta__config__{name}"
        if all(getattr(node, declare_attr, None) is None for node in chain):
            raise MissingMetaError(
                f"Missing '{declare_attr}', "
                f"this option has not been declared in any parents of {self!r}"
            )

        for node in chain:
            out = node.query_cfg_inst(name, default=NOT_SET)
            if out is not NOT_SET:
                return out

        if default is _REQUIRED:
            raise ConfigurationError(not_found)
        return default

    def query_cfg_inst(self, name, default=_REQUIRED):
        """Query a setting on this node only (dict/list values are copied).

        Lookup: ``self._<name>``, ``self.Meta.<name>``, ``self.meta__<name>``,
        then *default*. Raises ``IndexError`` when nothing matches.
        """
        out = getattr(self, f"_{name}", NOT_SET)
        if out is NOT_SET:
            out = getattr(getattr(self, "Meta", None), name, NOT_SET)
        if out is NOT_SET:
            out = getattr(self, f"meta__{name}", NOT_SET)
        if out is NOT_SET:
            if default is _REQUIRED:
                raise IndexError(
                    f"Setting '{name}' has not been declared before being used"
                    f" in '{self!r}'"
                )
            return default

        if isinstance(out, (dict, list)):
            out = copy.copy(out)
        return out
