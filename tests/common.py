import re

REGEX_RULES = [
    # matches "<object at 0xHEXPATTERN>"
    (r"<([^>]+) at 0x[0-9a-fA-F]+>", r"<\1>"),
    # Fall back for project
    (r"\S+/python-clak", r"/app/python-clak"),  # matches python-clak/ root project
    (r"\S+/[^/]*clak[^/]*", r"/app/python-clak"),  # matches *clak*/ root project
    # Home overrides
    (r"/home/[^/]+/", r"/home/user/"),  # matches /home/USER/
    # Match eceptions lines
    (r"line [0-9]+,", r"line XXX,"),
]


def replace_with_placeholders(input_str: str, regex_rules: list[str] = None) -> str:
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

        old = result
        result = re.sub(regex, replace, result)

        # if old != result:
        #     print ("MODIFIED")
    return result


# TEST = "o 'cli_run' method found for <examples.demo103_nested.AppMain object at 0x7ff5836045b0>"

# out = replace_with_placeholders(TEST)

# print(out)
