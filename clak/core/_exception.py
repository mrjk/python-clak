"""Exception handler chain for ParserNode (clean_terminate)."""

import logging
import os
import sys

from clak import exception

# Same logger as parser.py so tests can patch clak.core.parser.logger
logger = logging.getLogger("clak.core.parser")


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


class ExceptionMixin:  # pylint: disable=too-few-public-methods
    """Paasify-style terminate chain used by ``dispatch()``."""

    @staticmethod
    def _exception_exit_code(err, default=1):
        rc = getattr(err, "rc", default)
        return rc if isinstance(rc, int) else default

    @staticmethod
    def _exception_advice(err):
        advice = getattr(err, "advice", None)
        if isinstance(advice, str):
            logger.warning(advice)

    def _terminate_app_exception(self, err):
        """Default handler for app exceptions (Paasify-style: rc + message)."""
        self._exception_advice(err)
        print(err, file=sys.stderr)
        rc = self._exception_exit_code(err)
        logger.critical(
            "Program exited with: error %s: %s",
            rc,
            err.__class__.__name__,
        )
        sys.exit(rc)

    @staticmethod
    def _iter_exception_entries(entries):
        for entry in entries or []:
            if isinstance(entry, (tuple, list)) and entry:
                exc_type = entry[0]
                handler = entry[1] if len(entry) > 1 else None
                yield exc_type, handler
            else:
                yield entry, None

    def _run_exception_handler(self, handler, err):
        if handler is None:
            self._terminate_app_exception(err)
            return
        result = handler(self, err)
        if isinstance(result, int):
            sys.exit(result)
        sys.exit(self._exception_exit_code(err))

    def clean_terminate(self, err, known_exceptions=None):
        """Handle program termination based on exception type.

        Processing order (Paasify-style chain):

        1. ``Meta.known_exceptions`` on the root parser (class or ``(class, handler)``)
        2. ``Meta.exception_handlers`` (third-party libs: YAML, shell, ...)
        3. Built-in Clak exceptions
        4. Broken pipe (``| head`` / ``| tail``) - quiet exit
        5. Common OS errors

        If nothing matches, return and let ``dispatch()`` report an unexpected bug.

        Args:
            err (Exception): The exception that triggered termination
            known_exceptions (list): List of exception types to handle specially
        """

        # 1. App-known exceptions (e.g. PaasifyError hierarchy)
        for exc_type, handler in self._iter_exception_entries(known_exceptions):
            if isinstance(err, exc_type):
                self._run_exception_handler(handler, err)

        # 2. Registered third-party / library handlers
        extra_handlers = self.query_cfg_parents("exception_handlers", default=[])
        for exc_type, handler in self._iter_exception_entries(extra_handlers):
            if isinstance(err, exc_type):
                self._run_exception_handler(handler, err)

        # 3. Clak parse errors - show usage first (leaf parser when known)
        if isinstance(err, exception.ClakParseError):
            if err.parser is not None:
                err.parser.print_usage()
            else:
                self.show_usage()
            print(f"{err}", file=sys.stderr)
            sys.exit(err.rc)

        # 4. User-facing Clak errors
        if isinstance(err, exception.ClakUserError):
            self._exception_advice(err)
            print(f"{err}", file=sys.stderr)
            sys.exit(err.rc)

        # 5. Other Clak errors (app / bug)
        if isinstance(err, exception.ClakError):
            err_name = err.__class__.__name__
            self._exception_advice(err)
            err_message = err.message or err.__doc__
            print(f"{err}", file=sys.stderr)
            logger.critical(
                "Program exited with bug %s(%s): %s",
                err_name,
                err.rc,
                err_message,
            )
            sys.exit(err.rc)

        # 6. Broken pipe from | head / | tail - quiet exit (no bug log)
        if isinstance(err, BrokenPipeError):
            _exit_broken_pipe()

        # 7. OS errors (BrokenPipeError already handled above)
        if isinstance(err, OSError):
            logger.critical("Program exited with OS error: %s", err)
            sys.exit(err.errno if err.errno is not None else 1)
