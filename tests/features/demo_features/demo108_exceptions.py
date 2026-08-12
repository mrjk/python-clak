#!/usr/bin/env python3

"""
This is a demo that illustrate a basic usage of Meta class.

Purpose: 
  - Illustrate how to use Meta to customize parser behavior
"""

import sys

import clak.exception as exception

# import os
# import logging
from clak import Argument, Command, Parser

# logger = logging.getLogger(__name__)


class CustomError(Exception):
    """A custom error for demonstration."""

    rc = 1


def handle_custom_error(_app, err):
    """Custom handler for CustomError; return int exit code."""
    print(f"Caught CustomError: {err}", file=sys.stderr)
    print("This is handled by our custom handler!", file=sys.stderr)
    return 42


class AppException(Exception):
    "Custom App exception"


class AppCommand1(Parser):
    "Command 1, should raise ClakNotImplementedError exception"


class AppCommand2(Parser):
    "Command 2, raise custom exceptions"

    def cli_run(self, destination=None, name=None, **_):
        raise AppException("Custom exception")


class AppCommand3(Parser):
    "Command 3, raise custom exceptions, uncaught"

    def cli_run(self, destination=None, name=None, **_):
        raise RuntimeError("Runtime exception")


class AppMain(Parser):
    """
    Demo application with exception handlers

    """

    class Meta:
        "Store Main app settings"

        known_exceptions = [
            (CustomError, handle_custom_error),
            AppException,
        ]

    # Define two subcommands
    command1 = Command(AppCommand1, help="Execute command 1")
    command2 = Command(AppCommand2, help="Execute command 2")
    command3 = Command(AppCommand3, help="Execute command 3")


if __name__ == "__main__":

    # Instanciate your app, parse command line and run appropiate command.
    AppMain()
