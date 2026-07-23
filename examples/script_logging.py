#!/usr/bin/env python3
"""Demo: structured CLI logging with LoggingOptMixin.

Try:
  ./script_logging.py
  ./script_logging.py -v
  ./script_logging.py -vv
  ./script_logging.py -vvv
  ./script_logging.py -vv --log-format extended
  ./script_logging.py greet Ada
"""

from __future__ import annotations

import logging

from clak import Argument, Command, LoggingOptMixin, Parser

logger = logging.getLogger(__name__)


class GreetCmd(Parser):
    """Greet someone and emit logs at several levels."""

    name = Argument("NAME", help="Name to greet", default="World", nargs="?")

    def cli_run(self, name="World", **_):
        self.logger.debug("Preparing greeting for %s", name)
        self.logger.info("Hello, %s", name)
        self.logger.success("Greeting delivered")
        self.logger.notice("Tip: pass -v / -vv for more detail")
        print(f"Hello, {name}!")


class AppMain(LoggingOptMixin, Parser):
    """Logging demo.

    ``Meta.log_levels`` lists cumulative ``-v`` tiers as ``LEVEL|logger``.
    An empty logger name configures the root logger.
    """

    class Meta:
        log_prefix = __name__
        log_default_level = "WARNING"
        log_levels = [
            ["WARNING|" + __name__],  # default
            ["INFO|" + __name__],  # -v
            ["DEBUG|" + __name__],  # -vv
            ["DEBUG|"],  # -vvv (root — includes clak internals)
        ]
        # Kept at WARNING until maximum verbosity (-vvv here)
        log_silent = ["urllib3", "asyncio"]

    greet = Command(GreetCmd)

    def cli_run(self, **_):
        logger.warning("App module logger (logging.getLogger(__name__))")
        self.logger.info("Parser logger (self.logger) — visible from -v")
        self.logger.debug("Debug line — visible from -vv")
        print("Run a subcommand, e.g. greet — or pass -h")


if __name__ == "__main__":
    AppMain()
