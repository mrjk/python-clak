"""Exception handler chain run by dispatch (``clean_terminate``)."""

import logging
import os
import sys

from clak import exception

logger = logging.getLogger(__name__)


def _exit_broken_pipe(rc=1):
    """Exit quietly after BrokenPipeError (e.g. ``| head`` / ``| tail``).

    Redirects stdout to ``/dev/null`` so Python's shutdown flush does not print
    ``Exception ignored ... BrokenPipeError``.
    """
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except Exception:  # pylint: disable=broad-exception-caught
        try:
            sys.stdout.close()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    sys.exit(rc)


def _exit_code(err, default=1):
    rc = getattr(err, "rc", default)
    return rc if isinstance(rc, int) else default


def _log_advice(err):
    advice = getattr(err, "advice", None)
    if isinstance(advice, str):
        logger.warning(advice)


def _iter_exception_entries(entries):
    """``(exception type, handler or None)`` from ``cls`` / ``(cls, handler)``."""
    for entry in entries or []:
        if isinstance(entry, (tuple, list)) and entry:
            yield entry[0], (entry[1] if len(entry) > 1 else None)
        else:
            yield entry, None


def _run_exception_handler(node, handler, err):
    """Exit through *handler* (int result = rc), or Paasify-style default."""
    if handler is None:
        _log_advice(err)
        print(err, file=sys.stderr)
        rc = _exit_code(err)
        logger.critical("Program exited with: error %s: %s", rc, type(err).__name__)
        sys.exit(rc)
    result = handler(node, err)
    sys.exit(result if isinstance(result, int) else _exit_code(err))


def clean_terminate(node, err, known_exceptions=None):
    """Exit the program for a dispatch error, or return if nothing matches.

    Processing order (Paasify-style chain):

    1. ``Meta.known_exceptions`` on the root parser (class or ``(class, handler)``)
    2. ``Meta.exception_handlers`` (third-party libs: YAML, shell, ...)
    3. Clak parse errors (usage first), user errors, other Clak errors
    4. Broken pipe (``| head`` / ``| tail``) - quiet exit
    5. Common OS errors

    If nothing matches, ``dispatch()`` reports an unexpected bug.
    """
    extra_handlers = node.query_cfg_parents("exception_handlers", default=[])
    for entries in (known_exceptions, extra_handlers):
        for exc_type, handler in _iter_exception_entries(entries):
            if isinstance(err, exc_type):
                _run_exception_handler(node, handler, err)

    if isinstance(err, exception.ClakParseError):
        # Show usage first (leaf parser when known)
        if err.parser is not None:
            err.parser.print_usage()
        else:
            node.show_usage()
        print(f"{err}", file=sys.stderr)
        sys.exit(err.rc)

    if isinstance(err, exception.ClakError):
        _log_advice(err)
        print(f"{err}", file=sys.stderr)
        if not isinstance(err, exception.ClakUserError):
            logger.critical(
                "Program exited with bug %s(%s): %s",
                type(err).__name__,
                err.rc,
                err.message or err.__doc__,
            )
        sys.exit(err.rc)

    if isinstance(err, BrokenPipeError):
        _exit_broken_pipe()

    if isinstance(err, OSError):
        logger.critical("Program exited with OS error: %s", err)
        sys.exit(err.errno if err.errno is not None else 1)
