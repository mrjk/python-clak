"""Shared helpers for regression output normalization."""

import re
import sys

import sh

# ---------------------------------------------------------------------------
# Python compatibility flags
# Name pattern: COMPAT_<TOPIC>_PY<ver>
# Set from the running interpreter; flip to False to disable a quirk later.
# ---------------------------------------------------------------------------

_PY = sys.version_info[:2]

# Python 3.11+ traceback caret / wavy-underline annotation lines
COMPAT_TRACEBACK_CARETS_PY311 = _PY >= (3, 11)

# Python 3.13+ changed builtin ``str.__doc__`` (demo101 prints ``__name__.__doc__``)
COMPAT_STR_DOC_PY313 = _PY >= (3, 13)


def _build_regex_rules() -> list:
    rules = [
        # Strip ANSI color / style escapes (TTY vs CI)
        (r"\x1b\[[0-9;]*m", r""),
        # matches "<object at 0xHEXPATTERN>"
        (r"<([^>]+) at 0x[0-9a-fA-F]+>", r"<\1>"),
        # Fall back for project
        (r"\S+/python-clak", r"/app/python-clak"),  # matches python-clak/ root project
        (r"\S+/[^/]*clak[^/]*", r"/app/python-clak"),  # matches *clak*/ root project
        # Home overrides
        (r"/home/[^/]+/", r"/home/user/"),  # matches /home/USER/
        # Match eceptions lines
        (r"line [0-9]+,", r"line XXX,"),
        # Path rewrite can drop the opening quote: File /app/...py" → File "/app/...py"
        (r'File (/app/python-clak[^"]*")', r'File "\1'),
    ]

    if COMPAT_TRACEBACK_CARETS_PY311:
        rules.append(
            # Python 3.11+ traceback caret / wavy underline lines
            (r"(?m)^[ \t]*[~^]+[ \t]*\n?", r""),
        )

    if COMPAT_STR_DOC_PY313:
        rules.append(
            # str.__doc__ wording changed in 3.13
            (
                r"encoding defaults to 'utf-8'\.",
                r"encoding defaults to sys.getdefaultencoding().",
            ),
        )

    return rules


REGEX_RULES = _build_regex_rules()


def run_cli_script(script_path, cli_args):
    """Run a demo script via ``sh``; return ``(output, exit_code)``.

    Uses ``_truncate_exc=False`` so long tracebacks are not clipped in
    ``str(ErrorReturnCode)`` (version/size dependent otherwise).
    """
    demo_script = sh.Command(script_path)
    try:
        output = demo_script(
            *cli_args, _err_to_out=True, _tty_out=True, _truncate_exc=False
        )
        return str(output), 0
    except sh.ErrorReturnCode as err:
        return str(err), int(err.exit_code)


def replace_with_placeholders(input_str: str, regex_rules: list = None) -> str:
    """
    Replace matched content in input string with placeholders based on regex rules.

    Args:
        input_str: The input string to process
        regex_rules: List of regex patterns to match and replace

    Returns:
        String with matched patterns replaced by PLACEHOLDER

    Example:
        >>> text = "Error at line 123: Invalid token"
        >>> rules = [r"\\d+", r"Error at"]
        >>> replace_with_placeholders(text, rules)
        'PLACEHOLDER line PLACEHOLDER: Invalid token'
    """
    input_str = str(input_str)
    regex_rules = regex_rules or REGEX_RULES
    result = input_str
    for rule in regex_rules:
        regex = rule[0]
        try:
            replace = rule[1]
        except IndexError:
            replace = "PLACEHOLDER"

        result = re.sub(regex, replace, result)

    return result


def cli_case_ids(cases) -> list:
    """Stable pytest ids for ``(cli_args, expected_output, expected_exit)`` cases.

    The id comes from argv only, so regression snapshot names survive edits to
    the expected text and reordering of cases. Repeated argv gets ``#2``,
    ``#3``... Raises if two ids would map to the same snapshot file name
    (pytest-regressions replaces non-word characters with ``_``).
    """
    ids = []
    seen = {}
    for case in cases:
        base = " ".join(case[0]) or "no-args"
        seen[base] = seen.get(base, 0) + 1
        ids.append(base if seen[base] == 1 else f"{base} #{seen[base]}")

    files = {}
    for case_id in ids:
        fname = re.sub(r"\W", "_", case_id)
        if fname in files:
            raise ValueError(
                f"Case ids {files[fname]!r} and {case_id!r} share snapshot name "
                f"{fname!r}; reword one cli_args"
            )
        files[fname] = case_id
    return ids


def use_settings(monkeypatch, **changes):
    """Override process ClakSettings fields for one test (auto-restored)."""
    from clak.runtime.settings import (  # pylint: disable=import-outside-toplevel
        ClakSettings,
    )

    monkeypatch.setattr(
        ClakSettings, "_current", ClakSettings.current().replace(**changes)
    )


def block_imports(monkeypatch, *prefixes):
    """Make ``import <prefix>...`` raise ImportError (simulate a missing extra)."""
    import builtins  # pylint: disable=import-outside-toplevel

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.split(".", 1)[0] in prefixes:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
