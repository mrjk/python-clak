from types import SimpleNamespace
import logging
import copy

logger = logging.getLogger(__name__)


class NullType:
    """
    A special type that behaves as a replacement for None.
    We have to put a new default value to know if a variable has been set by
    the user explicitly. This is useful for the ``CommandLine`` loader, when
    CLI parsers force you to set a default value, and thus, break the discovery
    chain.
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
    "Represent an unset arg"

    def repr(self):
        return "<NOT_SET>"

class UnSetArg(NullType):
    "Represent an unset arg"

    def repr(self):
        return "<UNSET_ARG>"


class Failure(NullType):
    "Represent a failure"

    def repr(self):
        return "<FAILURE>"

class Default(NullType):
    "Represent a default"

    def repr(self):
        return "<DEFAULT>"


NOT_SET = NotSet()
UNSET_ARG = UnSetArg()
FAILURE = Failure()
DEFAULT = Default()


class Fn(SimpleNamespace):
    """A simple namespace that keep in memomy its init arguments."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs



class Node():
    "New version and simpler version of node"

    name: str = None
    parent: "Node" = None

    class Meta:
        """Class to store class-level configuration overrides."""


    def __init__(self, name=UNSET_ARG, parent=None):

        # Initialize name
        self.name = name if name is not UNSET_ARG else f"{self.__class__.__name__}()" #({hex(id(self))})"
        assert isinstance(self.name, str) # To unit test

        # Initialize parent
        self.parent = parent
        assert isinstance(self.parent, (Node, type(None))) # To unit test


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


    def get_fname(self, attr="key"):
        "Return the full name of the parser"
        parents = self.get_hierarchy()
        if parents:
            fname = [x.get_name(attr=attr, default=None) or "" for x in parents]
            return ".".join(fname) or ""
        return ""


    def query_cfg_parents(
        self,
        name,
        as_subkey=False,
        cast=None,
        default=UNSET_ARG,
        include_self=True,
        report=False,
    ):
        """Query configuration from parent object.

        Args:
            name: Configuration setting name to query
            as_subkey: If True and parent value is dict, get self.key from it
            cast: Optional type to cast the result to
            default: Default value if setting is not found

        Returns:
            The configuration value from the parent, optionally cast to specified type

        Raises:
            UnknownSetting: If no parent exists and no default is provided
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
            raise Exception(msg)
        
        # Prepare lookup chain
        _report = []
        parents = self.get_hierarchy()
        if include_self is False:
            # Remove itself from hierarchy
            parents = parents[:-1]  # Changed from parents[1:] to parents[:-1]
        parents.reverse()  # Start from self/immediate parent
        out = NOT_SET

        for parent in parents:
            _report.append(f"Check '{name}' in parent {parent}")

            # Check for _name attribute directly first
            val = getattr(parent, f"_{name}", NOT_SET)
            if val is not NOT_SET:
                out = val
                _report.append(f"Found '{name}' in parent {parent}= {out}")
                break

            # If not found in direct attribute, try query_cfg_inst
            try:
                out, _report2 = parent.query_cfg_inst(name, default=NOT_SET, report=True)
                _report.append(_report2)
                if out is not NOT_SET:
                    _report.append(f"Found '{name}' in parent {parent}= {out}")
                    break
            except IndexError:
                continue

        if out is NOT_SET:
            _report.append(f"NotFound '{name}' in parent: {parent}")
        if out is NOT_SET and default is not UNSET_ARG:
            out = default
        elif out is NOT_SET:
            msg = (
                f"Setting '{name}' has not been declared in hierarchy of '{repr(self)}'"
            )
            raise Exception(msg)

        if report:
            return out, _report
        return out


    def query_cfg_inst(self, name, override=None, default=UNSET_ARG, report=False):
        "Query configuration from instance"

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


class Node_v1:
    """Base class for configuration objects providing core configuration query functionality.

    This class implements the basic configuration query mechanisms used by all configuration
    classes. It supports querying configuration values from various sources including
    instance attributes, class Meta attributes, and parent configurations.
    """

    class Meta:
        """Class to store class-level configuration overrides."""

    def __init__(self, key=None, value=NOT_SET, parent=None):
        """Initialize a configuration base instance.

        Args:
            key: The configuration key name
            value: The configuration value (defaults to NOT_SET)
            parent: Parent configuration object if this is a child config
        """
        self.key = key
        self._parent = parent
        self._value = value
        self._cache = True  # TOFIX

    # Instance config management
    # ----------------------------

    def query_inst_cfg(self, *args, cast=None, report=False, **kwargs):
        """Query instance configuration with optional type casting.

        Args:
            *args: Variable length argument list passed to _query_inst_cfg
            cast: Optional type to cast the result to
            **kwargs: Arbitrary keyword arguments passed to _query_inst_cfg

        Returns:
            The configuration value, optionally cast to the specified type
        """
        out, _report = self._query_inst_cfg(*args, **kwargs)
        logger.debug("Node config query for %s.%s=%s", self, args[0], out)

        if isinstance(out, (dict, list)):
            out = copy.copy(out)

        if cast is not None:
            # Try to cast if asked
            if not out:
                out = cast()
            assert isinstance(
                out, cast
            ), f"Wrong type for config {self}, expected {cast}, got: {type(out)} {out}"
        if report:
            return out, _report
        return out

    # @classmethod
    # def _query_cls_cfg(cls, *args, **kwargs):
    #     "Temporary class method"
    #     out = cls._query_inst_cfg(cls, *args, **kwargs)
    #     if isinstance(out, (dict, list)):
    #         out = copy.copy(out)
    #     return out

    def _query_inst_cfg(self, name, override=None, default=UNSET_ARG):
        """Internal method to query instance configuration from various sources.

        Searches for configuration values in the following order:
        1. Dictionary override if provided
        2. Instance attribute with _name prefix
        3. Class Meta attribute
        4. Instance attribute with meta__ prefix
        5. Default value if provided

        Args:
            name: Configuration setting name to query
            override: Optional dictionary of override values
            parents: Whether to check parent configurations
            default: Default value if setting is not found

        Returns:
            Tuple of (value, query_sources) where query_sources is a list of searched locations

        Raises:
            UnknownSetting: If the setting is not found and no default is provided
        """
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

        if default is not UNSET_ARG:
            query_from.append("default_arg")
            return default, query_from

        msg = (
            f"Setting '{name}' has not been declared before being used"
            f" in '{repr(self)}', tried to query: {query_from}"
        )
        raise exceptions.UnknownSetting(msg)

    def query_cfg(self, name, include_self=True, report=False, **kwargs):
        "Temporary wrapper"
        return self.query_parent_cfg(name, include_self=True, report=report, **kwargs)

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def query_parent_cfg(
        self,
        name,
        as_subkey=False,
        cast=None,
        default=UNSET_ARG,
        include_self=False,
        report=False,
    ):
        """Query configuration from parent object.

        Args:
            name: Configuration setting name to query
            as_subkey: If True and parent value is dict, get self.key from it
            cast: Optional type to cast the result to
            default: Default value if setting is not found

        Returns:
            The configuration value from the parent, optionally cast to specified type

        Raises:
            UnknownSetting: If no parent exists and no default is provided
        """

        # Fast exit or raise exception
        if not self._parent and include_self is False:
            if default is not UNSET_ARG:
                if report:
                    return default, "No parents, return default value"
                return default
            msg = (
                f"Setting '{name}' has not been declared in hierarchy of '{repr(self)}'"
            )
            raise exceptions.UnknownSetting(msg)

        # Check parents
        _report = []
        parents = self.get_hierarchy()
        if include_self is False:
            parents = parents[1:]
        out = NOT_SET
        for parent in parents:
            _report.append(f"Check '{name}' in parent {parent}")

            if report:
                out, _report2 = parent.query_inst_cfg(
                    name, default=NOT_SET, report=True
                )
                _report.append(_report2)
            else:
                out = parent.query_inst_cfg(name, default=NOT_SET)

            # If a value is found, then scan it
            if out is not NOT_SET:
                _report.append(f"Found '{name}' in parent {parent}= {out}")

                # Ckeck subkey
                if as_subkey is True:
                    if isinstance(out, dict):
                        out = out.get(self.key, NOT_SET)
                    elif isinstance(out, list):
                        assert isinstance(self.key, int), f"Got: {self.key}"
                        out = out[self.key]
                    else:
                        out = NOT_SET
                _report.append(f"Found2 '{name}' in parent {parent}= {out}")

            # Don't ask more parents if value is found
            if out is not NOT_SET:
                break

        if out is NOT_SET:
            _report.append(f"NotFound '{name}' in parent: {parent}")

        if cast is not None:
            # Try to cast if asked
            if not out:
                out = cast()
            assert isinstance(
                out, cast
            ), f"Wrong type for config {name}, expected {cast}, got: {type(out)} {out}"

        if out is NOT_SET and default is UNSET_ARG:
            msg = (
                f"Setting '{name}' has not been declared in hierarchy of '{repr(self)}'"
            )
            raise exceptions.UnknownSetting(msg)

        if report:
            return out, _report
        return out

    def get_hierarchy(self):
        "Return a list of parents NEW VERSION"
        out = [self]

        target = self
        while target._parent is not None and target._parent not in out:
            target = target._parent
            out.append(target)

        return out
