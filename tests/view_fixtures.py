"""Shared fixtures for view unit tests."""

import re

USERS = [
    {"name": "ada", "role": "admin", "city": "London"},
    {"name": "linus", "role": "dev", "city": "Helsinki"},
]

USERS_UNSORTED = [
    {"name": "linus", "role": "dev", "city": "Helsinki"},
    {"name": "ada", "role": "admin", "city": "London"},
    {"name": "grace", "role": "dev", "city": "New York"},
]


def _option_flags(app):
    return {opt for action in app.parser._actions for opt in action.option_strings}


def _has_background_csi(text: str) -> bool:
    """True if *text* sets a token/pane background (not default-bg or underline)."""
    if "\x1b[48;" in text:
        return True
    for seq in re.findall(r"\x1b\[([0-9;]*)m", text):
        if not seq:
            continue
        for code in seq.split(";"):
            if not code:
                continue
            number = int(code)
            if 40 <= number <= 47 or number == 48 or 100 <= number <= 107:
                return True
    return False
