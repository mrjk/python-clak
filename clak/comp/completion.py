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
import argparse
import logging
import os
import sys
from pprint import pprint
from types import SimpleNamespace

import argcomplete

from clak.parser import Argument, Parser

# PEP 366
__package__ = "argcomplete.scripts"

logger = logging.getLogger(__name__)

# Completion support
# ============================


class CompRenderMixin:
    "Completion support Methods"

    def print_completion_stdout(self, args):

        sys.stdout.write(
            argcomplete.shellcode(
                args.executable,
                args.use_defaults,
                args.shell,
                args.complete_arguments,
                args.external_argcomplete_script,
            )
        )


class CompRenderCmdMixin(CompRenderMixin):
    "Completion command support"

    use_defaults = Argument(
        "--no-defaults",
        # dest="use_defaults",
        action="store_false",
        default=True,
        help="when no matches are generated, do not fallback to readline's default completion (affects bash only)",
    )
    complete_arguments = Argument(
        "--complete-arguments",
        nargs=argparse.REMAINDER,
        help="arguments to call complete with; use of this option discards default options (affects bash only)",
    )
    shell = Argument(
        "-s",
        "--shell",
        choices=("bash", "zsh", "tcsh", "fish", "powershell"),
        default="bash",
        help="output code for the specified shell",
    )
    external_argcomplete_script = Argument(
        "-e",
        "--external-argcomplete-script",
        help=argparse.SUPPRESS,
        # help="external argcomplete script for auto completion of the executable"
    )
    executable = Argument(
        "--executable",
        nargs="+",
        help=argparse.SUPPRESS,
        default=["my_app_name"],
    )

    def cli_run(self, ctx, **kwargs):

        print("COMPLETION")
        self.print_completion_stdout(ctx)
        print("COMPLETION")


class CompRenderOptMixin(CompRenderMixin):
    "Completion options support"
    completion_cmd = Argument(
        "--completion",
        action="store_true",
        help="output code for the specified shell",
    )

    def cli_run(self, ctx, **kwargs):

        args = ctx.args

        kwargs = {
            "executable": ["my_app_name"],
            "shell": "bash",
            "use_defaults": True,
            "complete_arguments": [],
            "external_argcomplete_script": None,
        }
        if args.completion_cmd is True:
            self.print_completion_stdout(SimpleNamespace(**kwargs))
        else:
            super().cli_run(ctx, **kwargs)


# Command configuration
# ============================


class CompCmdRender(CompRenderCmdMixin, Parser):
    pass


# class CompOptRender(CompRenderOptMixin, Parser):
#     pass
