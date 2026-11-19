"""Plugin helpers: mixin hook registration for Parser nodes."""

# pylint: disable=too-few-public-methods

import logging
import warnings
from typing import Any, Protocol

logger = logging.getLogger(__name__)

CLI_HOOK_PREFIX = "cli_hook__"


class ClakHookHost(Protocol):
    """Parser node that may expose ``cli_hook__*``, ``cli_run``, ``cli_group``."""

    _cli_hooks: dict

    def cli_run(self, **kwargs: Any) -> Any:
        """Leaf command implementation."""

    def cli_group(self, ctx: Any, **kwargs: Any) -> Any:
        """Group-level command behavior."""


class PluginHelpers:
    """Mixin helper: register methods onto a parser instance.

    ``hook_register`` stores callables on ``cli_methods`` and, for names
    starting with ``cli_hook__``, on ``_cli_hooks``. It does not setattr
    the method onto the instance.
    """

    cli_methods = None

    def hook_register(self, name, instance, force=False):
        """Register a method from this plugin onto *instance*.

        Meant to be used from mixin code.

        Args:
            name (str): Name of the method to register
            instance: Parser node to register the hook on
            force (bool, optional): Replace an existing registration.
                    Defaults to False.

        Raises:
            AttributeError: If the specified method is not found on self

        Example:
            >>> cls.hook_register("test_log", self)

        .. deprecated:: 0.6.2
            Define ``cli_hook__*`` methods on a mixin instead; they are
            collected automatically. Removal planned for 0.7.
        """
        warnings.warn(
            "PluginHelpers.hook_register is deprecated; define cli_hook__* "
            "methods on a mixin instead (removal planned for 0.7)",
            DeprecationWarning,
            stacklevel=2,
        )
        methods_dict = getattr(instance, "cli_methods", None)
        if methods_dict is None:
            methods_dict = {}
            setattr(instance, "cli_methods", methods_dict)

        hooks = getattr(instance, "_cli_hooks", None)
        if hooks is None:
            hooks = {}
            setattr(instance, "_cli_hooks", hooks)

        if name in methods_dict and force is False:
            return

        new_method = getattr(self, name, None)
        if new_method is None:
            raise AttributeError(f"Method {name} not found in instance {self}")

        def _wrapper(*args, **kwargs):
            if "instance" not in kwargs:
                kwargs["instance"] = instance
            return new_method(*args, **kwargs)

        methods_dict[name] = _wrapper
        if name.startswith(CLI_HOOK_PREFIX):
            # Dispatch calls hooks as hook(walk_node, ctx): pass the bound
            # method as-is so ``instance`` is not supplied twice.
            hooks[name] = new_method
        logger.debug(
            "Registered plugin method %s.%s = %s",
            instance,
            name,
            _wrapper.__qualname__,
        )
