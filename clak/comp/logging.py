"""
Provides logging functionality and configuration for CLI applications.

This module implements a flexible logging system with the following key features:
- Configurable log levels and verbosity through CLI arguments
- Support for colored output (when coloredlogs is installed)
- Multiple log formatters (default, extended, audit, debug)
- Hierarchical logger naming with prefix/suffix support
- Mixin class for easy integration with CLI parsers

The logging system can be configured through Meta settings in parser classes:
- log_prefix: Sets the base name for loggers (typically __name__)
- log_suffix: Controls the right part of logger names
- log_default_level: Sets the default logging level

Notes:
- `log_prefix` must be enabled to allow CLI logging.



Example:

    class AppMain(LoggingOptMixin,Parser):


        class Meta:

            log_prefix = f"{__name__}"    # AKA myapp
            # log_prefix = f"other_prefix.{__name__}"
            # log_prefix = f"{__name__}.other_prefix"
            # log_suffix = "suffix"

        def cli_group(self, ctx, **_):
            "Main group"

            # Usual logger, usually from logger = logging.getLogger(__name__)
            logger.debug("Hello World - App")
            logger.info("Hello World - App")
            logger.warning("Hello World - App")
            logger.error("Hello World - App")

            # Only useful when `log_prefix` is set
            self.logger.debug("Hello World - Self")
            self.logger.info("Hello World - Self")
            self.logger.warning("Hello World - Self")
            self.logger.error("Hello World - Self")

            
Without log_prefix set (by default):
```
 WARNING myapp.cli                 Hello World - App
   ERROR myapp.cli                 Hello World - App
 WARNING clak.parser               Hello World - Self
   ERROR clak.parser               Hello World - Self
```


With log_prefix set:
```
 WARNING myapp.cli                 Hello World - App
   ERROR myapp.cli                 Hello World - App
 WARNING myapp.cli.AppMain         Hello World - Self
   ERROR myapp.cli.AppMain         Hello World - Self
```

"""

import argparse
import logging
import logging.config
from types import SimpleNamespace

from clak.exception import ClakAppError
from clak.parser import Argument, MetaSetting
from clak.plugins import PluginHelpers
from clak.settings import CLAK_COLORS, LOG_FORMAT, LOG_STYLES

# import sys
# from types import SimpleNamespace


# from pprint import pprint


# pylint: disable=invalid-name
coloredlogs = None
if CLAK_COLORS:
    try:
        import coloredlogs  # type: ignore
    except ImportError:
        pass


if coloredlogs:
    coloredlogs.DEFAULT_LEVEL_STYLES = LOG_STYLES
    coloredlogs.DEFAULT_LOG_FORMAT = LOG_FORMAT

# PEP 366
# __package__ = "argcomplete.scripts"

logger = logging.getLogger(__name__)


# See:
# /home/jez/volumes/data/prj/jez/lab/iam-python/iam/lib/logs.py
# /home/jez/volumes/data/prj/mrjk/bench_paasify/python-paasify__work__v4/cafram/cafram/utils.py
# /home/jez/volumes/data/prj/mrjk/bench_paasify/python-paasify__work__v4/cafram/cafram/utils.py


# Note: The cli should be configrable as well
# VERBOSITY_PARSER_LEVELS = ["{__name__}.cli", "{__name__}", "clak", ""]  # Root parser
# VERBOSITY_LEVELS2 = [
#     ("{__name__}.cli", logging.INFO),
#     ("{__name__}.cli", logging.DEBUG),
#     ("{__name__}", logging.DEBUG),
#     # Future
#     # [
#     #     ("{__name__}", logging.DEBUG),
#     #     ("clak", logging.INFO),
#     # ],
#     # [
#     #     ("{__name__}", logging.DEBUG),
#     #     ("clak", logging.DEBUG),
#     # ],
#     # [
#     #     ("{__name__}", logging.DEBUG),
#     #     ("", logging.INFO),
#     # ],
#     ("", logging.DEBUG),
# ]


# Logging support
# ============================

# VERBOSITY_LEVELS = {
#     0: logging.ERROR,  # Default
#     1: logging.WARNING,  # Default
#     2: logging.INFO,  # -v
#     3: logging.DEBUG,  # -vv
#     4: logging.DEBUG,  # -vvv (more detailed)
#     5: logging.DEBUG,  # -vvvv (most detailed)
# }

# LOGGING_LEVELS, a var containing the mapping between log levels and names
LOGGING_LEVELS = dict(
    zip(
        logging._nameToLevel.values(),  # pylint: disable=protected-access
        logging._nameToLevel.keys(),  # pylint: disable=protected-access
    )
)

DEFAULT_LOG_LEVEL = logging.WARNING
DEFAULT_LOG_LEVELS = [
    ["INFO|clak"],
    ["DEBUG|clak"],
    ["INFO|"],
    ["DEBUG|"],
]

# Logging helpers
# ================


# # pylint: disable=redefined-builtin
# def get_app_verbosity(verbosity, vars=None):
#     "Get app verbosity level"
#     error = None
#     vars = vars or {}
#     max_ = len(VERBOSITY_LEVELS2)
#     if verbosity >= max_:
#         error = f"Verbosity already set to max: {verbosity}/{max_-1}"
#         verbosity = max_ - 1
#     elif verbosity < 0:
#         error = f"Verbosity too low, setting to min: {verbosity}/{max_-1}"
#         verbosity = 0

#     logger_name = VERBOSITY_LEVELS2[verbosity][0]
#     logger_name = logger_name.format(**vars)

#     out = SimpleNamespace(
#         verbosity=verbosity,
#         logger_name=logger_name,
#         logger_level=VERBOSITY_LEVELS2[verbosity][1],
#         error=error,
#     )
#     return out


# Imported from python-iam
def get_app_logger(loggers=None, level="WARNING", colors=False, formatter="default"):
    "Instanciate application logger"

    loggers = loggers or {}

    # Settings
    fclass = "logging.Formatter"
    # msconds = ""
    if colors and coloredlogs:
        # Require coloredlogs
        fclass = "coloredlogs.ColoredFormatter"
        # msconds = "%(msecs)03d"

    # Define formatters
    formatters = {
        "default": {
            "()": fclass,
            "format": LOG_FORMAT,
            # "format": "[%(levelname)8s] %(message)s",
            # 'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        "extended": {
            "()": fclass,
            "format": "[%(levelname)8s] %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "audit": {
            "()": fclass,
            "format": "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "debug": {
            "()": fclass,
            "format": "%(msecs)03d %(levelname)8s %(name)-30s %(message)-80s"
            "\t[%(filename)s/%(funcName)s:%(lineno)d]",
            "datefmt": "%H:%M:%S",
        },
    }

    # Assert arguments
    if formatter not in formatters:
        choice = ",".join(formatters.keys())
        raise ValueError(
            f"Invalid formatter: '{formatter}', please choose one of: {choice}"
        )

    # Logging config
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,  # Breaks exisitng logger if True
        # How logs looks like
        "formatters": formatters,
        # Where goes the logs
        "handlers": {
            "default": {
                "level": level,
                "formatter": formatter,
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",  # Default is stderr
            },
        },
        # Where logs come from
        "loggers": {
            # Used to catch ALL logs
            "": {  # root logger
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": False,
            },
            # # Used to catch all logs of myapp and sublibs
            # 'myapp': {
            #     'handlers': ['default'],
            #     'level': 'INFO',
            #     'propagate': False
            # },
            # # Used to catch cli logs only
            # 'myapp.cli': {
            #     'handlers': ['default'],
            #     'level': 'INFO',
            #     'propagate': False
            # },
            # # Used to catch app components, instanciated loggers
            # 'myapp.comp': {
            #     'handlers': ['default'],
            #     'level': 'DEBUG',
            #     'propagate': False
            # },
        },
    }

    # Prepare logger components
    for name, conf in loggers.items():
        logging_config["loggers"][name] = {
            "propagate": False,
            "handlers": ["default"],
        }
        logging_config["loggers"][name].update(conf)

    # print("APPLIED CONFIG")
    # pprint(logging_config["loggers"])

    # Load logger
    logging.config.dictConfig(logging_config)

    # print("EFFECTIVE LEVEL", logging.getLogger().getEffectiveLevel())


#########################################################


class LoggingOptMixin(PluginHelpers):
    "Logging options support"

    verbosity = Argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (-v, -vv, -vvv, -vvvv)",
    )

    log_format = Argument(
        "--log-format",
        choices=["default", "extended", "audit", "debug"],
        help="Set log formatter",
        # help=argparse.SUPPRESS,
        default="default",
    )

    app_trace_mode = Argument(
        "--trace",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Enable trace logging on errors",
    )

    if coloredlogs:
        log_colors = Argument(
            "--log-colors",
            default=True,
            action=argparse.BooleanOptionalAction,
            help="Enable colored logs",
        )

    # Meta settings
    meta__config__log_prefix = MetaSetting(
        help="Prefix of the logger name, usually set to __name__. Required to enable logging.",
    )
    meta__config__log_suffix = MetaSetting(
        help="Suffix of the logger name, override the right part.",
    )
    meta__config__log_default_level = MetaSetting(
        help="Default log level of the logger, usually WARNING, INFO or DEBUG",
    )

    meta__config__log_levels = MetaSetting(
        help="List of log levels to use, usually INFO and DEBUG",
    )

    meta__config__log_silent = MetaSetting(
        help="List of loggers to silent, usually too verbose loggers",
    )

    logger = None

    @staticmethod
    def _log_level(value):
        "Return a validated numeric logging level."
        if isinstance(value, int):
            return value
        if not isinstance(value, str):
            raise TypeError(f"Log level must be a string or integer, got {type(value)}")
        level = logging._nameToLevel.get(
            value.upper()
        )  # pylint: disable=protected-access
        if level is None:
            choices = ", ".join(
                sorted(logging._nameToLevel)
            )  # pylint: disable=protected-access
            raise ValueError(f"Unknown log level '{value}', choose one of: {choices}")
        return level

    def assemble_user_config(self, configs):
        """Build cumulative verbosity tiers from ``Meta.log_levels``.

        Explicit entries use ``LEVEL|logger``. Legacy configurations containing
        only logger names are expanded to INFO and DEBUG tiers for each group.
        """
        if not isinstance(configs, list) or not configs:
            raise ValueError("log_levels must be a non-empty list of lists")
        if not all(isinstance(tier, list) for tier in configs):
            raise TypeError("Each log_levels tier must be a list")

        entries = [entry for tier in configs for entry in tier]
        if not all(isinstance(entry, str) for entry in entries):
            raise TypeError("Each log_levels entry must be a string")

        legacy = all("|" not in entry for entry in entries)
        if legacy:
            configs = [
                [f"{logging.getLevelName(level)}|{logger_name}" for logger_name in tier]
                for tier in configs
                for level in (logging.INFO, logging.DEBUG)
            ]

        user_config = []
        for idx, lvl_config in enumerate(configs):
            final = []
            for entry in lvl_config:
                if "|" in entry:
                    level_name, logger_name = entry.split("|", maxsplit=1)
                    level = self._log_level(level_name)
                else:
                    logger_name = entry
                    level = (logging.INFO, logging.DEBUG)[idx % 2]
                final.append(
                    SimpleNamespace(
                        logger_name=logger_name,
                        level=level,
                    )
                )
            user_config.append(final)
        return user_config

    def select_user_config(self, user_config, req=0):
        "Select user config from requested level"
        max_level = len(user_config) - 1
        if not isinstance(req, int) or req < 0 or req > max_level:
            raise ClakAppError(
                f"Verbosity must be between 0 and {max_level}, got {req}"
            )

        req_config = {}
        for idx, logger_config in enumerate(user_config):
            if idx > req:
                break

            for logger_ns in logger_config:
                logger_name = logger_ns.logger_name
                req_config[logger_name] = {
                    "handlers": ["default"],
                    "level": logger_ns.level,
                    "propagate": False,
                }

        return SimpleNamespace(
            config=req_config,
            max_level=max_level,
            level=req,
        )

    def cli_hook__logging(self, instance, ctx, **_):
        "Inject or create logger into instance"

        logger.debug("Load Logging hook for %s", instance)

        log_prefix = self.query_cfg_parents(
            "log_prefix", default=None, include_self=True
        )
        log_suffix = self.query_cfg_parents(
            "log_suffix", default=None, include_self=True
        )

        if ctx.cli_first:
            log_levels = self.query_cfg_parents(
                "log_levels", default=None, include_self=True
            )
            log_silent = self.query_cfg_parents(
                "log_silent", default=None, include_self=True
            )
            log_default_level = self.query_cfg_parents(
                "log_default_level", default=DEFAULT_LOG_LEVEL, include_self=True
            )
            if log_default_level is None:
                log_default_level = DEFAULT_LOG_LEVEL
            log_verbosity = ctx.args.verbosity
            log_colors = ctx.args.get("log_colors", False)

            log_silent = log_silent or []
            if not isinstance(log_silent, list) or not all(
                isinstance(name, str) for name in log_silent
            ):
                raise TypeError("log_silent must be a list of logger names")

            user_config = self.assemble_user_config(log_levels or DEFAULT_LOG_LEVELS)
            log_config = self.select_user_config(user_config, req=log_verbosity)

            logger_config = {
                "": {  # root logger
                    "handlers": ["default"],
                    "level": self._log_level(log_default_level),
                    "propagate": False,
                },
            }
            logger_config.update(log_config.config)

            logs_silenced = log_verbosity < log_config.max_level
            if logs_silenced:
                for logger_name in log_silent:
                    logger_config[logger_name] = {
                        "handlers": ["default"],
                        "level": logging.WARNING,
                        "propagate": False,
                    }

            get_app_logger(
                loggers=logger_config,
                level=logging.NOTSET,
                formatter=ctx.args.log_format,
                colors=log_colors,
            )

            logger.info(
                "Logging set to %s/%s",
                log_verbosity,
                log_config.max_level,
            )
            for name, conf in logger_config.items():
                logger.info("  %s: %s", logging.getLevelName(conf["level"]), name)
            if log_silent:
                if logs_silenced:
                    logger.info("Logging to WARNING: %s", ", ".join(log_silent))
                else:
                    logger.info("All configured logs are shown")

        # Create internal logger instance if not already created
        if log_suffix is None:
            log_suffix = "==FLAT=="

        if log_suffix == argparse.SUPPRESS:
            suffix = ""
        elif log_suffix == "==FLAT==":
            suffix = f".{instance.__class__.__name__}"
        elif log_suffix == "==NESTED==":
            suffix = str(instance.get_fname(attr="key"))
            if suffix and not suffix.startswith("."):
                suffix = f".{suffix}"
        else:
            suffix = str(log_suffix)
            if suffix and not suffix.startswith("."):
                suffix = f".{suffix}"

        log_name = instance.__class__.__module__
        if log_prefix is not None:
            log_name = f"{log_prefix}{suffix}"
        instance.logger = logging.getLogger(log_name)
        logger.debug("Enable logging for '%s': %s", instance, log_name)

        # Register plugin methods
        self.hook_register("test_logger", instance)

        logger.debug("Logging hook loaded for %s", instance)

        ctx.plugins.update(
            {
                "log_acquired_root_logger": True,
                "log_prefix": log_prefix,
                "log_suffix_req": log_suffix,
                "log_suffix": suffix,
            }
        )

    def test_logger(self, instance: object | None = None) -> None:
        """Test the logger by sending test messages at different log levels.

        Args:
            instance: The instance to test logging for. If None, uses self.
        """
        instance = instance if instance else self
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
