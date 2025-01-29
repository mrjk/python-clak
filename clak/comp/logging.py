#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

"""
Register a Python executable for use with the argcomplete module.

To perform the registration, source the output of this script in your bash shell
(quote the output to avoid interpolation).

Example:

    $ eval "$(register-python-argcomplete my-favorite-script.py)"

For Tcsh

    $ eval `register-python-argcomplete --shell tcsh my-favorite-script.py`

For Fish

    $ register-python-argcomplete --shell fish my-favourite-script.py > ~/.config/fish/my-favourite-script.py.fish
"""
import os
import argparse
import logging
import sys
from types import SimpleNamespace
from pprint import pprint

import argcomplete
from clak.parser import Argument, Parser
from clak.plugins import PluginHelpers

# PEP 366
__package__ = "argcomplete.scripts"

logger = logging.getLogger(__name__)



# Logging support
# ============================

VERBOSITY_LEVELS = {
    0: logging.ERROR,     # Default
    1: logging.WARNING,   # Default
    2: logging.INFO,      # -v
    3: logging.DEBUG,     # -vv
    4: logging.DEBUG,     # -vvv (more detailed)
    5: logging.DEBUG      # -vvvv (most detailed)
}

# LOGGING_LEVELS, a var conatinng the mapping between log levels and names
LOGGING_LEVELS=dict(zip(logging._nameToLevel.values(), logging._nameToLevel.keys()))


def get_logger_level(log_level=None, verbosity=None, level=None):
    "Resolve log level from string"
    out = None

    if verbosity is not None:
        out = VERBOSITY_LEVELS.get(verbosity, None)

        if not out:
            raise ValueError(f"Invalid verbosity level: {verbosity}")

    elif log_level is not None:

        if isinstance(log_level, str):
            log_level = log_level.upper()
            log_level = log_level.replace("WARN", "WARNING")
            out = getattr(logging, log_level, None)
        elif isinstance(log_level, int):
            out = log_level
        
        if out is None:
            raise ValueError(f"Invalid log level: {log_level}")
    
    elif level is not None:
        # transform logging level to verbosity level string name
        #  where level in an logging level, like logging.DEBUG.

        assert False, "Invalid function call"

    return out



class LoggingOptMixin(PluginHelpers):
    "Logging options support"


    verbosity = Argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase verbosity level (-v, -vv, -vvv, -vvvv)"
    )




    # # arguments_dict = {
    # # completion = Argument('--completion', choices=['bash', 'zsh', 'sh'], help='Generate completion script')
    # log_level = Argument('--log-level', choices=['debug', 'info', 'warning', 'error', 'critical'], help='Set log level')
    # debug = Argument('--debug', action='store_true', help='Enable debug mode')
    # trace = Argument('--trace', action='store_true', help='Enable trace mode')
    # # trace = Argument('--trace', choices=['clak', 'cli', 'lib'], help='Set log scope')
    # # }

    # logger_level = Argument('--logger-level', 
    #                     choices=['debug', 'info', 'warning', 'error', 'critical'], 
    #                     # help='Set log level'
    #                     help=argparse.SUPPRESS,
    #                     default="info")

    logger_level_default = Argument('--logger-level', 
                        choices=['debug', 'info', 'warning', 'error', 'critical'], 
                        # help='Set log level'
                        help=argparse.SUPPRESS,
                        default=logging.WARNING)


    # prog_name = Argument('--prog-name', 
    #                      help=argparse.SUPPRESS,
    #                      default="My_app")



    # def set_logger_level(self, log_level):
    #     "Set instance logger level"
    #     logging.basicConfig(level=get_logger_level(log_level))

    logger = None
    # _public_logger = False

    def cli_hook__logging(self, instance, ctx, **kwargs):
        "Inject or create logger into instance"


        log_prefix = self.query_cfg_parents("log_prefix", default=ctx.app_name, include_self=True)
        log_suffix = self.query_cfg_parents("log_suffix", default=None, include_self=True)
        log_level = self.query_cfg_parents("log_level", default=logging.INFO, include_self=True)
        


        # print("LoggingOptMixin.cli_hook__logging", instance, ctx, kwargs)

        # print ("PLUGINS", ctx.plugins.get("_public_logger", False) is False)
        # if ctx.plugins.get("_public_logger", False) is False:
        if ctx.cli_first:

            # Set root logger level
            # default_level = get_logger_level(ctx.args.logger_level_default)
            # default_level = ctx.app_log_level
            verbosity_level  = get_logger_level(ctx.args.verbosity)
            req_level = log_level - (verbosity_level * 10 )

            req_level = req_level if req_level > 0 else 0
            # print("REQ LEVEL", req_level)
            # pprint(LOGGING_LEVELS)
            # root_level = get_logger_level(req_level)
            logging.basicConfig(
                # level=logging.WARNING,  # Root logger level
                level=req_level,  # Root logger level
                # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                format='%(levelname)8s: %(name)s - %(message)s',
                stream=sys.stdout
            )
            if verbosity_level:
                logger.info("Verbosity level set to: %s - %s", req_level, LOGGING_LEVELS.get(req_level, "Unknown"))
            # ctx.plugins["_public_logger"] = True



        # Create internal logger instance if not already created
        # print ("HAS ATTR", getattr( instance, "logger", False))
        if getattr( instance, "logger", None) is None:
            # Retrieve prog_name from ctx

            suffix = log_suffix
            if log_suffix is None:
                log_suffix = '==FLAT=='

            if log_suffix == argparse.SUPPRESS:
                suffix = ""
            elif log_suffix == '==FLAT==':
                suffix = f".{instance.get_name(attr='key')}"
            elif log_suffix == '==NESTED==':
                suffix = f"{instance.get_fname(attr='key')}"


            log_name = f"{log_prefix}{suffix}"
            if instance.parent is None:
                instance.logger = logging.getLogger(log_name)
            elif True:
                instance.logger = logging.getLogger(log_name)
            else:
                instance.logger = instance.parent.logger

            # logger.debug("Enable logging for %s:%s", instance, log_name)
            instance.logger.debug("Enable logging for %s", instance)

        # Register plugin methods
        self.hook_register("test_logger", instance)

        self.logger.debug("Logging hook loaded for %s", instance)


        ctx.plugins.update({
            "log_acquired_root_logger": True,
            "log_prefix": log_prefix,
            "log_suffix_req": log_suffix,
            "log_suffix": suffix,
            "log_level": log_level
        })


    # TODO: All children instances must have the instance=None support ...
    def test_logger(self, instance=None):
        instance = instance if instance else self

        # print("Test log self=", self, "instance=", instance)
        # print("\n\n")
        # return
        instance.logger.debug("Test logger with DEBUG")
        instance.logger.info("Test logger with INFO")
        instance.logger.warning("Test logger with WARNING")
        instance.logger.error("Test logger with ERROR")
        instance.logger.critical("Test logger with CRITICAL")



# Command configuration
# ============================

# class CompCmdRender(CompRenderCmdMixin, Parser):
#     pass

# class CompOptRender(CompRenderOptMixin, Parser):
#     pass


# if __name__ == "__main__":
#     sys.exit(main())