"Common utils"


def deindent_docstring(text, reindent=False):
    # If first line is empty, and second line starts with a space or tab,
    # then extract the second line indent, and remove it from all lines
    out = text
    lines = text.split("\n")
    if len(lines) > 1 and lines[0] == "":
        indent = lines[1][:len(lines[1]) - len(lines[1].lstrip())]
        out = "\n".join([line[len(indent):] if line.startswith(indent) else line for line in lines])
    
    if isinstance(reindent, str) and reindent:
        # Reindent all lines
        out = "\n".join([reindent + line if line.strip() else line for line in out.split("\n")])
    
    return out


