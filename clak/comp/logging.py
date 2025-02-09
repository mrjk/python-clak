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

# import sys
from types import SimpleNamespace

# from pprint import pprint


try:
    import coloredlogs  # type: ignore
except ImportError:
    coloredlogs = None
# coloredlogs = None

from clak.parser import Argument, MetaSetting
from clak.plugins import PluginHelpers

if coloredlogs:
    coloredlogs.DEFAULT_LEVEL_STYLES = {
        "spam": {"color": "grey", "faint": True},
        "debug": {"color": "magenta"},
        "verbose": {"color": "cyan"},
        "info": {"color": "blue"},
        "notice": {"color": "green"},
        "warning": {"color": "yellow"},
        "success": {"color": "green", "bold": True},
        "error": {"color": "red"},
        "critical": {"color": "red", "bold": True},
    }


# PEP 366
# __package__ = "argcomplete.scripts"

logger = logging.getLogger(__name__)


# TODO:
# 0: INFO - __name__.cli: Always displayed
# 1: DEBUG - __name__.cli: Show debug cli
# 2: DEBUG - __name__
# 3: TRACE1 - __name__
# 4: TRACE2 - __name__
# 5: TRACE3 - __name__
# 6: DEBUG - root
# --trace: Show python exception at any time, for debugging


# See:
# /home/jez/volumes/data/prj/jez/lab/iam-python/iam/lib/logs.py
# /home/jez/volumes/data/prj/mrjk/bench_paasify/python-paasify__work__v4/cafram/cafram/utils.py
# /home/jez/volumes/data/prj/mrjk/bench_paasify/python-paasify__work__v4/cafram/cafram/utils.py


# Note: The cli should be configrable as well
VERBOSITY_PARSER_LEVELS = ["{__name__}.cli", "{__name__}", "clak", ""]  # Root parser
VERBOSITY_LEVELS2 = [
    ("{__name__}.cli", logging.INFO),
    ("{__name__}.cli", logging.DEBUG),
    ("{__name__}", logging.DEBUG),
    # Future
    # [
    #     ("{__name__}", logging.DEBUG),
    #     ("clak", logging.INFO),
    # ],
    # [
    #     ("{__name__}", logging.DEBUG),
    #     ("clak", logging.DEBUG),
    # ],
    # [
    #     ("{__name__}", logging.DEBUG),
    #     ("", logging.INFO),
    # ],
    ("", logging.DEBUG),
]

# Logging support
# ============================

VERBOSITY_LEVELS = {
    0: logging.ERROR,  # Default
    1: logging.WARNING,  # Default
    2: logging.INFO,  # -v
    3: logging.DEBUG,  # -vv
    4: logging.DEBUG,  # -vvv (more detailed)
    5: logging.DEBUG,  # -vvvv (most detailed)
}

# LOGGING_LEVELS, a var containing the mapping between log levels and names
LOGGING_LEVELS = dict(
    zip(
        logging._nameToLevel.values(),  # pylint: disable=protected-access
        logging._nameToLevel.keys(),  # pylint: disable=protected-access
    )
)

# Logging helpers
# ================


# pylint: disable=redefined-builtin
def get_app_verbosity(verbosity, vars=None):
    "Get app verbosity level"
    error = None
    vars = vars or {}
    max_ = len(VERBOSITY_LEVELS2)
    if verbosity >= max_:
        error = f"Verbosity already set to max: {verbosity}/{max_-1}"
        verbosity = max_ - 1
    elif verbosity < 0:
        error = f"Verbosity too low, setting to min: {verbosity}/{max_-1}"
        verbosity = 0

    logger_name = VERBOSITY_LEVELS2[verbosity][0]
    logger_name = logger_name.format(**vars)

    out = SimpleNamespace(
        verbosity=verbosity,
        logger_name=logger_name,
        logger_level=VERBOSITY_LEVELS2[verbosity][1],
        error=error,
    )
    return out


# Imported from python-iam
def get_app_logger(loggers=None, level="WARNING", colors=False, formatter="default"):
    "Instanciate application logger"

    loggers = loggers or {}

    # Settings
    fclass = "logging.Formatter"
    # msconds = ""
    if colors:
        # Require coloredlogs
        fclass = "coloredlogs.ColoredFormatter"
        # msconds = "%(msecs)03d"

    # Define formatters
    formatters = {
        "default": {
            "()": fclass,
            "format": "[%(levelname)8s] %(message)s",
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
            "format": "%(msecs)03d %(levelname)8s %(name)-30s %(message)s"
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
            "info": {
                "level": "INFO",
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


# Deprecated
# def get_logger_level(log_default_level=None, verbosity=None, level=None):
#     "Resolve log level from string"
#     out = None

#     if verbosity is not None:
#         out = VERBOSITY_LEVELS.get(verbosity, None)
#         if not out:
#             raise ValueError(f"Invalid verbosity level: {verbosity}")

#     elif log_default_level is not None:

#         if isinstance(log_default_level, str):
#             log_default_level = log_default_level.upper()
#             log_default_level = log_default_level.replace("WARN", "WARNING")
#             out = getattr(logging, log_default_level, None)
#         elif isinstance(log_default_level, int):
#             out = log_default_level

#         if out is None:
#             raise ValueError(f"Invalid log level: {log_default_level}")

#     elif level is not None:
#         # transform logging level to verbosity level string name
#         #  where level in an logging level, like logging.DEBUG.

#         assert False, "Invalid function call"

#     return out


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

    if coloredlogs:
        log_colors = Argument(
            "--log-colors",
            default=True,
            action=argparse.BooleanOptionalAction,
            help="Enable colored logs",
        )

    logger_level_default = Argument(
        "--logger-level",
        choices=["debug", "info", "warning", "error", "critical"],
        # help='Set log level'
        help=argparse.SUPPRESS,
        default=logging.WARNING,
    )

    # prog_name = Argument('--prog-name',
    #                      help=argparse.SUPPRESS,
    #                      default="My_app")

    # def set_logger_level(self, log_default_level):
    #     "Set instance logger level"
    #     logging.basicConfig(level=get_logger_level(log_default_level))

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
    # meta__config__log_enabled = MetaSetting(
    #     help="Enable logging for the instance",
    # )

    logger = None
    # _public_logger = False

    def cli_hook__logging(self, instance, ctx, **_):
        "Inject or create logger into instance"

        # log_enabled = self.query_cfg_parents(
        #     "log_enabled", default=False, include_self=True
        # )
        log_prefix = self.query_cfg_parents(
            "log_prefix", default=None, include_self=True
        )
        # app_proc_module = self.query_cfg_parents(
        #     "app_proc_module", default=None, include_self=True
        # )
        log_suffix = self.query_cfg_parents(
            "log_suffix", default=None, include_self=True
        )
        log_default_level = self.query_cfg_parents(
            "log_default_level", default=logging.INFO, include_self=True
        )
        # print("log_prefix", log_prefix)
        # print("app_proc_module", app_proc_module)
        # log_prefix = log_prefix if isinstance(log_prefix, str) else app_proc_module
        # log_prefix = log_prefix if isinstance(log_prefix, str) else "clak.cli"
        # pprint(ctx.__dict__)

        # print("LoggingOptMixin.cli_hook__logging", instance, ctx, kwargs)

        # print ("PLUGINS", ctx.plugins.get("_public_logger", False) is False)
        # if ctx.plugins.get("_public_logger", False) is False:
        if ctx.cli_first:

            # pprint(ctx.__dict__)

            cfg = get_app_verbosity(
                ctx.args.verbosity, vars={"__name__": ctx.log_prefix}
            )

            log_colors = ctx.args.get("log_colors", False)
            log_config = {
                "": {  # root logger
                    "handlers": ["default"],
                    "level": "WARNING",
                    "propagate": False,
                },
                f"{cfg.logger_name}": {  # app logger
                    "handlers": ["default"],
                    "level": cfg.logger_level,
                    "propagate": False,
                },
            }

            get_app_logger(
                loggers=log_config,
                level=cfg.logger_level,
                formatter=ctx.args.log_format,
                colors=log_colors,
            )

            logger.debug("Requested logging configuration: %s", cfg)
            logger.debug("Root logger configuration: %s", log_config)
            if cfg.error:
                logger.info(cfg.error)

        # Create internal logger instance if not already created

        suffix = log_suffix
        if log_suffix is None:
            log_suffix = "==FLAT=="

        if log_suffix == argparse.SUPPRESS:
            suffix = ""
        elif log_suffix == "==FLAT==":
            name = instance.__class__.__name__
            suffix = f".{name}"
        elif log_suffix == "==NESTED==":
            suffix = f"{instance.get_fname(attr='key')}"

        # enabled_instance_logging = False
        # if log_enabled and getattr(instance, "logger", None) is None:
        # if log_enabled:

        if log_prefix is not None:

            # Retrieve prog_name from ctx

            log_name = f"{log_prefix}{suffix}"
            # print("YOOOOOO", log_name)
            if instance.parent is None:
                instance.logger = logging.getLogger(log_name)
            else:
                instance.logger = logging.getLogger(log_name)
            # else:
            #     instance.logger = instance.parent.logger

            logger.debug("Enable logging for '%s': %s", instance, log_name)
            # instance.logger.debug("Enable logging for %s", instance)

        # Register plugin methods
        self.hook_register("test_logger", instance)

        logger.debug("Logging hook loaded for %s", instance)

        ctx.plugins.update(
            {
                "log_acquired_root_logger": True,
                "log_prefix": log_prefix,
                "log_suffix_req": log_suffix,
                "log_suffix": suffix,
                "log_default_level": log_default_level,
            }
        )

    def test_logger(self, instance: object | None = None) -> None:
        """Test the logger by sending test messages at different log levels.

        Args:
            instance: The instance to test logging for. If None, uses self.
        """
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
