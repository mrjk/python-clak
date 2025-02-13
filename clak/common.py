"""Common utility functions for text processing and string manipulation.

This module provides helper functions for working with text, particularly
around handling docstring indentation and formatting.
"""


def replace_tabs(text, value=None):
    """Replace all tabs with spaces in a text string.

    Args:
        text (str): The text to process
        spaces (int): Number of spaces to replace each tab with. Defaults to 2.

    Returns:
        str: The text with tabs replaced by spaces
    """
    if not isinstance(text, str):
        return text
    value = value if isinstance(value, str) else "  "
    return text.replace("\t", value)


def deindent_docstring(text, reindent=False):
    """
    Remove indentation from a docstring.

    If the first line is empty and the second line starts with whitespace,
    extracts that whitespace as the indentation level and removes it from all lines.

    Args:
        text (str): The docstring text to process
        reindent (str|bool): If a string is provided, reindents all lines with that string.
                            If False, no reindentation is performed.

    Returns:
        str: The deindented (and optionally reindented) docstring
    """
    # If first line is empty, and second line starts with a space or tab,
    # then extract the second line indent, and remove it from all lines
    out = text
    lines = text.split("\n")
    if len(lines) > 1 and lines[0] == "":
        indent = lines[1][: len(lines[1]) - len(lines[1].lstrip())]
        out = "\n".join(
            [line[len(indent) :] if line.startswith(indent) else line for line in lines]
        )

    if isinstance(reindent, str) and reindent:
        # Reindent all lines
        out = "\n".join(
            [reindent + line if line.strip() else line for line in out.split("\n")]
        )

    return out


def to_boolean(value):
    "Convert anything to boolean value"

    if isinstance(value, bool):
        return value

    value = str(value).lower()

    default_values = {
        "1": True,
        "true": True,
        "yes": True,
        "y": True,
        "on": True,
        "t": True,
        "0": False,
        "false": False,
        "no": False,
        "n": False,
        "off": False,
        "f": False,
    }

    try:
        return default_values[value]
    except KeyError:
        raise ValueError(f"Invalid boolean value: {value}") from None


class ObjectNamespace:
    """A simple attribute-based namespace."""

    # see also: https://dev.to/taqkarim/extending-simplenamespace-for-nested-dictionaries-58e8

    def __init__(self, **kwargs):
        self.__dict__ = {}
        self.__dict__.update(kwargs)  # or self.__dict__ = kwargs

    def __repr__(self):
        keys = sorted(k for k in self.__dict__ if not k.startswith("_"))
        return f"{type(self).__name__}[{', '.join(keys)}]"

    def get(self, key, default=None):
        "Return the value for key if key is in the dictionary, else default."
        return self.__dict__.get(key, default)

    def update(self, **kwargs):
        "Update the dictionary with the key-value pairs from kwargs."
        self.__dict__.update(kwargs)

    def __getattr__(self, key):
        return self.__dict__.get(key, None)

    def __setattr__(self, key, value):
        self.__dict__[key] = value

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)
