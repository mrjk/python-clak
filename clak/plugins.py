import logging
import sys
from pprint import pprint
from types import SimpleNamespace

logger = logging.getLogger(__name__)


# MixinSupport Helpers
# ============================
def is_bound(m):
    return hasattr(m, "__self__")


class PluginHelpers:
    "General helper tools for plugins"

    cli_methods = None

    # @classmethod
    def hook_register(self, name, instance, force=False):
        """This method allow to call class method hooks

        Meant to be used in class methods

        >>> cls.hook_register("test_log", self)
        """
        # setattr(self, name, cls_method)

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
            raise Exception(f"Method {name} not found in instance {self}")

        # This wrapper rewrap anything, even existing methods
        def _wrapper(*args, **kwargs):
            bounded = is_bound(new_method)
            # print("\n\nWRAPPERD", bounded, instance, name,new_method)

            # if bounded:
            if not "instance" in kwargs:
                # kwargs["instance"] = instance.__class__.__name__
                kwargs["instance"] = instance
            # print("EXEC", new_method, "args=", args, "kwargs=" , kwargs)

            return new_method(*args, **kwargs)

        # fn_new = new_method
        # fn_new = wrapper
        fn_new = _wrapper
        # fn_new = lambda *args, **kwargs: new_method(self,instance, *args, **kwargs)
        # fn_new = lambda *args, **kwargs: new_method(instance, *args, **kwargs)
        # fn_new = lambda *args, **kwargs: new_method(*args, **kwargs)

        # print ("REGISTER METHOD", instance, name, fn_new)

        # Register saved commadns
        methods_dict[name] = fn_new
        setattr(instance, name, fn_new)
        logger.debug("Registered plugin method %s.%s = %s", instance, name, fn_new)
