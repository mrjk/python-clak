#!/usr/bin/env python3
"""Demo: Paasify-style CLI error handling with Clak.

The whole program is wrapped in try/except inside ``Parser.dispatch()``.
Errors flow through ``clean_terminate()``:

  1. ``Meta.known_exceptions``     — your app exception tree (with ``rc``)
  2. ``Meta.exception_handlers``   — third-party libs (YAML, shell, …)
  3. Built-in Clak exceptions
  4. OS errors
  5. No match → full traceback + "report to developer"

Try:
  ./script_exceptions.py deploy myapp
  ./script_exceptions.py deploy missing          # rc 44
  ./script_exceptions.py load bad.yaml           # YAML handler, rc 42
  ./script_exceptions.py broken                  # unexpected bug (traceback)
  ./script_exceptions.py --trace broken          # traceback before handler chain
  CLAK_DEBUG=1 ./script_exceptions.py broken     # same as --trace
"""

from __future__ import annotations

import logging
import sys

import yaml

from clak import Argument, Command, LoggingOptMixin, Parser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App exception tree (see paasify/errors.py, paasify_v4/exception.py)
# ---------------------------------------------------------------------------


class AppError(Exception):
    "Base application error."

    rc = 1
    advice = None

    def __init__(self, message, rc=None, advice=None):
        self.advice = advice
        if rc is not None:
            self.rc = rc
        super().__init__(message)


class AppNotFound(AppError):
    "Unknown application."

    rc = 44


class InvalidConfig(AppError):
    "Invalid configuration file."

    rc = 36


# ---------------------------------------------------------------------------
# Third-party handlers (see paasify/cli.py clean_terminate)
# ---------------------------------------------------------------------------


def handle_yaml_parser_error(_app, err):
    logger.critical(err)
    logger.critical("Invalid YAML file (syntax or structure)")
    sys.exit(42)


APPS = {"myapp": {"name": "myapp", "config": "app.yml"}}


# ---------------------------------------------------------------------------
# Commands — raise domain errors; no manual sys.exit()
# ---------------------------------------------------------------------------


class DeployCmd(Parser):
    "Deploy one application."

    name = Argument("NAME", help="Application name")

    def cli_run(self, name: str, **_):
        if name not in APPS:
            raise AppNotFound(
                f"application {name!r} not found",
                advice="Run: script_exceptions.py catalog list",
            )
        print(f"Deploying {name}")


class LoadCmd(Parser):
    "Load a YAML config (demo third-party handler)."

    path = Argument("PATH", help="YAML file path")

    def cli_run(self, path: str, **_):
        with open(path, encoding="utf-8") as handle:
            yaml.safe_load(handle)
        print(f"Loaded {path}")


class BrokenCmd(Parser):
    "Trigger an unexpected bug."

    def cli_run(self, **_):
        raise RuntimeError("unexpected failure in demo command")


class CatalogGroup(Parser):
    "Catalog operations."

    class ListCmd(Parser):
        "List known applications."

        def cli_run(self, **_):
            for name in APPS:
                print(name)

    list = Command(ListCmd)


class AppMain(LoggingOptMixin, Parser):
    """Exception-handling demo."""

    class Meta:
        log_prefix = __name__
        known_exceptions = [AppError]
        exception_handlers = [
            (yaml.parser.ParserError, handle_yaml_parser_error),
            (yaml.scanner.ScannerError, handle_yaml_parser_error),
        ]

    deploy = Command(DeployCmd)
    load = Command(LoadCmd)
    broken = Command(BrokenCmd)
    catalog = Command(CatalogGroup)


if __name__ == "__main__":
    AppMain()
