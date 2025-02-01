"""
Register a Python executable for use with the argcomplete module.

To perform the registration, source the output of this script in your bash shell
(quote the output to avoid interpolation).

Example:

    $ eval "$(register-python-argcomplete my-favorite-script.py)"

For Tcsh

    $ eval `register-python-argcomplete --shell tcsh my-favorite-script.py`

For Fish

    $ register-python-argcomplete --shell fish my-favourite-script.py \
        > ~/.config/fish/my-favourite-script.py.fish
"""

import argparse
import logging

# import os
import sys

# from pprint import pprint
from types import SimpleNamespace

import argcomplete

from clak.parser import Argument, Parser

# PEP 366
# __package__ = "argcomplete.scripts"

logger = logging.getLogger(__name__)

# Completion support
# ============================


class CompRenderMixin:  # pylint: disable=too-few-public-methods
    "Completion support Methods"

    def print_completion_stdout(self, args: SimpleNamespace) -> None:
        """Print completion script to stdout.

        Generates and outputs shell completion code for the specified executable using argcomplete.
        The completion script enables tab completion for commands and arguments.

        Args:
            args: Namespace containing completion configuration:
                executable: Name of executable to enable completion for
                use_defaults: Whether to fallback to readline defaults (bash only)
                shell: Target shell (bash, zsh, tcsh, fish, powershell)
                complete_arguments: Optional arguments to pass to complete command
                external_argcomplete_script: Optional external completion script
        """

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
        help="when no matches are generated, do not fallback to readline's"
        + " default completion (affects bash only)",
    )
    complete_arguments = Argument(
        "--complete-arguments",
        nargs=argparse.REMAINDER,
        help="arguments to call complete with; use of this option discards default"
        + " options (affects bash only)",
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

    def cli_run(self, ctx, **kwargs):  # pylint: disable=unused-argument
        """Command completion support mixin.

        Adds command completion support to parsers by providing arguments to configure
        shell completion behavior:

        - --no-defaults: Disable fallback to readline defaults (bash only)
        - --complete-arguments: Custom completion arguments (bash only)
        - --shell: Target shell (bash, zsh, tcsh, fish, powershell)
        - --executable: Name of executable to complete

        The mixin generates the appropriate shell completion code when run.
        Supports bash (default), zsh, tcsh, fish and powershell shells.

        Example:
            my-app completion  # Outputs bash completion code
            my-app completion --shell zsh  # Outputs zsh completion code
        """

        print("COMPLETION")
        self.print_completion_stdout(ctx)
        print("COMPLETION")


class CompRenderOptMixin(CompRenderMixin):
    """Completion options support mixin.

    Adds option completion support to parsers by providing a --completion flag
    that generates shell completion code. When used, outputs the appropriate
    completion code for the configured shell.

    The mixin adds:
    - --completion flag to generate shell completion code
    - Default completion behavior configuration
    - Shell-specific completion code generation

    Supports bash (default), zsh, tcsh, fish and powershell shells.
    """

    completion_cmd = Argument(
        "--completion",
        action="store_true",
        help="output code for the specified shell",
    )

    def cli_run(self, ctx, **kwargs):
        """Completion options support mixin.

        Adds option completion support to parsers by providing:
        - --completion flag to generate shell completion code
        - Default completion behavior configuration
        - Shell-specific completion code generation

        The mixin adds a --completion argument that when used will output the appropriate
        shell completion code. It supports:
        - bash (default)
        - zsh
        - tcsh
        - fish
        - powershell

        Example:
            my-app --completion  # Outputs bash completion code
            my-app --completion --shell zsh  # Outputs zsh completion code
        """

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
    """Command completion renderer class.

    Combines the CompRenderCmdMixin with the base Parser to create a class that can
    render command completion code. This class provides the core functionality for
    generating shell completion scripts for command-line tools.

    Key features:
    - Generates shell completion code for bash/tcsh/fish
    - Supports external completion scripts
    - Configurable executable names
    - Default completion behavior
    """


# class CompOptRender(CompRenderOptMixin, Parser):
#     pass
