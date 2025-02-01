"""Common utility functions for text processing and string manipulation.

This module provides helper functions for working with text, particularly
around handling docstring indentation and formatting.
"""


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
