"""Plugin system implementation for the clak framework.

This module provides the core plugin functionality, including helper classes and methods
for registering and managing plugins in the clak framework.
"""

# pylint: disable=too-few-public-methods

import logging

logger = logging.getLogger(__name__)


# MixinSupport Helpers
# ============================
def is_bound(method):
    """Check if a method is bound to an instance.

    Args:
        m: The method to check

    Returns:
        bool: True if the method is bound to an instance, False otherwise
    """
    return hasattr(method, "__self__")


class PluginHelpers:
    """General helper tools for plugins.

    This class provides utility methods for plugin management and registration.
    """

    cli_methods = None

    def hook_register(self, name, instance, force=False):
        """This method allow to call class method hooks.

        Meant to be used in class methods.

        Args:
            name (str): Name of the hook to register
            instance: Instance to register the hook on
            force (bool, optional): Whether to force registration even if already
                    exists. Defaults to False.

        Raises:
            AttributeError: If the specified method is not found in the instance

        Example:
            >>> cls.hook_register("test_log", self)
        """
        # Ensure methods_dict is initialized
        methods_dict = getattr(instance, "cli_methods", None)
        if methods_dict is None:
            methods_dict = {}
            setattr(instance, "cli_methods", methods_dict)

        # Skip if method is already registered unless force is True
        # if name in methods_dict or hasattr(instance, name):
        #     if force is False:
        #         return

        if name in methods_dict:
            if force is False:
                return

        # Ensure method is not already registered
        new_method = getattr(self, name, None)
        if new_method is None:
            raise AttributeError(f"Method {name} not found in instance {self}")

        # This wrapper rewrap anything, even existing methods
        def _wrapper(*args, **kwargs):
            if "instance" not in kwargs:
                kwargs["instance"] = instance
            return new_method(*args, **kwargs)

        fn_new = _wrapper

        # Register saved commands
        methods_dict[name] = fn_new
        setattr(instance, name, fn_new)
        logger.debug("Registered plugin method %s.%s = %s", instance, name, fn_new.__qualname__)
