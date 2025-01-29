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


# PEP 366
# __package__ = "argcomplete.scripts"

logger = logging.getLogger(__name__)



# Configuration and workdir support
# ============================


class XDGConfigMixin():
    "XDG configuration support"

    # config_dir = Argument('--config-dir', help=argparse.SUPPRESS, default=os.path.expanduser("~/.config/my_app"))

    # For AI:
    # This class should provide following arguments:
    # --conf-file = $XDG_CONFIG_HOME/my_app/config.yaml
    # --data-dir = $XDG_DATA_HOME/my_app
    # --cache-dir = $XDG_CACHE_HOME/my_app
    # --log-dir = $XDG_CACHE_HOME/my_app/logs

    # XDG base directories with defaults
    xdg_config = Argument('--conf-file', 
                             # help=argparse.SUPPRESS, 
                        help="Configuration file to use",
                        default=os.path.expanduser("~/.config/my_app/config.yaml")
                        )
    xdg_data_dir = Argument('--data-dir', help=argparse.SUPPRESS,
                       default=os.path.expanduser("~/.local/share/my_app"))
    xdg_cache_dir = Argument('--cache-dir', help=argparse.SUPPRESS,
                        default=os.path.expanduser("~/.cache/my_app"))
    xdg_log_dir = Argument('--log-dir', help=argparse.SUPPRESS,
                      default=os.path.expanduser("~/.cache/my_app/logs"))


# Command configuration
# ============================

# class CompCmdRender(CompRenderCmdMixin, Parser):
#     pass

# class CompOptRender(CompRenderOptMixin, Parser):
#     pass


# if __name__ == "__main__":
#     sys.exit(main())