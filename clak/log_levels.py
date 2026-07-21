"""Custom logging level registration for Clak applications."""

from __future__ import annotations

import logging
import warnings

#: Silently keep an existing level registration on conflict.
KEEP = "keep"
#: Keep an existing level registration and issue a warning.
KEEP_WARN = "keep-warn"
#: Silently overwrite an existing level registration.
OVERWRITE = "overwrite"
#: Overwrite an existing level registration and issue a warning.
OVERWRITE_WARN = "overwrite-warn"
#: Raise when a level registration conflicts.
RAISE = "raise"

# Built-in Clak levels. Method names must match ``CLAK_CUSTOM_LEVEL_STYLES``.
CLAK_CUSTOM_LEVELS = (
    ("SPAM", 5, "spam"),
    ("VERBOSE", 15, "verbose"),
    ("SUCCESS", logging.INFO + 3, "success"),
    ("NOTICE", logging.INFO + 5, "notice"),
)

# coloredlogs styles for custom levels (merged into ``LOG_STYLES`` in settings).
CLAK_CUSTOM_LEVEL_STYLES = {
    "spam": {"color": "grey", "faint": True},
    "verbose": {"color": "cyan"},
    "success": {"color": "green", "bold": True},
    "notice": {"color": "green"},
}

_missing_styles = {m for _, _, m in CLAK_CUSTOM_LEVELS} - set(CLAK_CUSTOM_LEVEL_STYLES)
_extra_styles = set(CLAK_CUSTOM_LEVEL_STYLES) - {m for _, _, m in CLAK_CUSTOM_LEVELS}
if _missing_styles or _extra_styles:
    raise RuntimeError(
        "CLAK_CUSTOM_LEVELS and CLAK_CUSTOM_LEVEL_STYLES out of sync: "
        f"missing={sorted(_missing_styles)} extra={sorted(_extra_styles)}"
    )


def add_logging_level(
    level_name,
    level_num,
    method_name=None,
    if_exists=KEEP_WARN,
    *,
    exc_info=False,
    stack_info=False,
):
    """Register a custom logging level on :py:mod:`logging`.

    Source: adapted from haggis / python-iam ``add_logging_level``.
    """

    def for_logger_adapter(self, msg, *args, **kwargs):
        kwargs.setdefault("exc_info", exc_info)
        kwargs.setdefault("stack_info", stack_info)
        self.log(level_num, msg, *args, **kwargs)

    def for_logger_class(self, msg, *args, **kwargs):
        if self.isEnabledFor(level_num):
            kwargs.setdefault("exc_info", exc_info)
            kwargs.setdefault("stack_info", stack_info)
            self._log(level_num, msg, args, **kwargs)

    def for_logging_module(*args, **kwargs):
        kwargs.setdefault("exc_info", exc_info)
        kwargs.setdefault("stack_info", stack_info)
        logging.log(level_num, *args, **kwargs)

    if not method_name:
        method_name = level_name.lower()
    if method_name == level_name:
        raise ValueError("Method name must differ from level name")

    items_found = 0
    items_conflict = 0

    def check_conflict(conflict, message):
        if conflict and if_exists == RAISE:
            raise AttributeError(message)
        return conflict

    def check_func_conflict(func, name, original_name, is_func, target):
        conflict = not (
            callable(func)
            and getattr(func, "_original_name", None) == original_name
            and getattr(func, "_exc_info", None) == exc_info
            and getattr(func, "_stack_info", None) == stack_info
        )
        return check_conflict(
            conflict,
            f"{'Function' if is_func else 'Method'} {name!r} already defined in {target}",
        )

    # ``_acquireLock`` / ``_releaseLock`` were removed in Python 3.14.
    _acquire = getattr(logging, "_acquireLock", None)
    _release = getattr(logging, "_releaseLock", None)
    if _acquire is None:
        _acquire = logging._lock.acquire  # pylint: disable=protected-access
        _release = logging._lock.release  # pylint: disable=protected-access

    _acquire()
    try:
        registered_num = logging.getLevelName(level_name)
        logger_class = logging.getLoggerClass()
        logger_adapter = logging.LoggerAdapter

        if registered_num != "Level " + level_name:
            items_found += 1
            items_conflict += check_conflict(
                registered_num != level_num,
                f"Level {level_name!r} already registered in logging module",
            )

        current_level = getattr(logging, level_name, None)
        if current_level is not None:
            items_found += 1
            items_conflict += check_conflict(
                current_level != level_num,
                f"Level {level_name!r} already defined in logging module",
            )

        logging_func = getattr(logging, method_name, None)
        if logging_func is not None:
            items_found += 1
            items_conflict += check_func_conflict(
                logging_func,
                method_name,
                for_logging_module.__name__,
                True,
                "logging module",
            )

        logger_method = getattr(logger_class, method_name, None)
        if logger_method is not None:
            items_found += 1
            items_conflict += check_func_conflict(
                logger_method,
                method_name,
                for_logger_class.__name__,
                False,
                "logger class",
            )

        adapter_method = getattr(logger_adapter, method_name, None)
        if adapter_method is not None:
            items_found += 1
            items_conflict += check_func_conflict(
                adapter_method,
                method_name,
                for_logger_adapter.__name__,
                False,
                "logger adapter",
            )

        if items_found > 0:
            if (items_conflict or items_found < 5) and if_exists in (
                KEEP_WARN,
                OVERWRITE_WARN,
            ):
                action = "Keeping" if if_exists == KEEP_WARN else "Overwriting"
                if items_conflict:
                    problem = "has conflicting definition"
                    items = items_conflict
                else:
                    problem = "is partially configured"
                    items = items_found
                warnings.warn(
                    f"Logging level {level_name!r} {problem} already "
                    f"({items}/5 items): {action}"
                )

            if if_exists in (KEEP, KEEP_WARN):
                return

        def label_func(func):
            func._original_name = func.__name__
            func.__name__ = method_name
            func._exc_info = exc_info
            func._stack_info = stack_info

        label_func(for_logging_module)
        label_func(for_logger_class)
        label_func(for_logger_adapter)

        logging.addLevelName(level_num, level_name)
        setattr(logging, level_name, level_num)
        setattr(logging, method_name, for_logging_module)
        setattr(logger_class, method_name, for_logger_class)
        setattr(logger_adapter, method_name, for_logger_adapter)
    finally:
        _release()


def register_clak_log_levels(if_exists=KEEP):
    """Register Clak's built-in custom levels (SPAM, VERBOSE, SUCCESS, NOTICE)."""
    for level_name, level_num, method_name in CLAK_CUSTOM_LEVELS:
        add_logging_level(level_name, level_num, method_name, if_exists=if_exists)
