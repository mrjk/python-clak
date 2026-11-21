"""Clak-owned --help layout and coloring (not an argparse HelpFormatter).

Walks ParserNode / HelpArg records. Does not regex argparse output.
``RichRecursiveHelpFormatter`` (Parser default) marks colored help: color
follows ``NO_COLOR``, ``CLAK_COLORS``, ``CLAK_COLOR_BACKEND``, TTY stdout, and
whether Rich is importable; otherwise the plain layout is printed.
"""

from __future__ import annotations

import sys
import textwrap
from argparse import OPTIONAL, SUPPRESS, ZERO_OR_MORE, RawDescriptionHelpFormatter
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from clak._optional import optional
from clak.runtime.rich_style import make_rich_console, render_markup_text
from clak.runtime.runtime import terminal_size
from clak.runtime.settings import (
    color_backend_uses_rich,
    colors_enabled,
    stream_isatty,
)

HELP_SUBCOMMANDS_TOP = "top"
HELP_SUBCOMMANDS_ALL = "all"
HELP_SUBCOMMANDS_CHOICES = frozenset({HELP_SUBCOMMANDS_TOP, HELP_SUBCOMMANDS_ALL})
HELP_NESTED_INDENT = "  "
MAX_HELP_POSITION = 30


def strip_rst_literals(text: Optional[str]) -> str:
    """Drop RST double-backticks from a Clak-owned help field."""
    if not text:
        return ""
    return text.replace("``", "")


@dataclass
class HelpLayout:
    """Listing policy for subcommands on one ParserNode."""

    subcommands: str = HELP_SUBCOMMANDS_ALL
    hide_parent: bool = True
    command_groups: tuple = ()
    collapsed_groups: tuple = ()  # option groups summarized in short --help
    help_all_flag: Optional[str] = None  # flag printing the full help

    def __post_init__(self):
        if self.subcommands not in HELP_SUBCOMMANDS_CHOICES:
            raise ValueError(
                "help_subcommands must be 'top' or 'all', " f"got {self.subcommands!r}"
            )
        if not isinstance(self.hide_parent, bool):
            raise ValueError(
                "help_hide_parent must be True or False, " f"got {self.hide_parent!r}"
            )
        if not isinstance(self.command_groups, tuple):
            self.command_groups = tuple(self.command_groups or ())


@dataclass(frozen=True)
class _HelpWidths:
    """Column widths for one --help listing."""

    action_width: int
    help_position: int
    help_width: int


@dataclass
class HelpArg:  # pylint: disable=too-many-instance-attributes
    """One attached argument, recorded at add_argument time."""

    dest: str
    option_strings: tuple
    help: Optional[str] = None
    default: Any = None
    nargs: Any = None
    metavar: Any = None
    required: bool = False
    choices: Any = None
    group: Optional[str] = None
    suppress: bool = False
    advanced: bool = False  # collapsed in short --help (help_level="advanced")

    @classmethod
    def from_action(cls, action, group=None, advanced=False) -> "HelpArg":
        """Build a HelpArg from an argparse Action."""
        help_msg = action.help
        suppress = help_msg == SUPPRESS
        return cls(
            dest=action.dest,
            option_strings=tuple(action.option_strings or ()),
            help=None if suppress else help_msg,
            default=action.default,
            nargs=action.nargs,
            metavar=action.metavar,
            required=bool(getattr(action, "required", False)),
            choices=getattr(action, "choices", None),
            group=group,
            suppress=suppress,
            advanced=advanced,
        )

    def is_positional(self) -> bool:
        """True when this argument has no option strings."""
        return not self.option_strings

    def is_hidden(self) -> bool:
        """True when help is suppressed or dest is a private name."""
        return self.suppress or (self.dest or "").startswith("__")


@dataclass
class HelpLine:
    """One output line as typed parts (kind, text)."""

    parts: list[tuple[str, str]] = field(default_factory=list)

    def append(self, kind: str, text: str) -> None:
        """Append a typed part when text is non-empty."""
        if text:
            self.parts.append((kind, text))


@dataclass
class HelpDocument:
    """Structured help: lines of typed parts, rendered plain or styled."""

    lines: list[HelpLine] = field(default_factory=list)

    def to_plain(self) -> str:
        """Render lines as a string."""
        return "".join(
            "".join(text for _kind, text in line.parts) + "\n" for line in self.lines
        )

    def add(self, *parts: tuple[str, str]) -> None:
        """Append one line made of ``(kind, text)`` parts (none: blank line)."""
        line = HelpLine()
        for kind, text in parts:
            line.append(kind, text)
        self.lines.append(line)


class RecursiveHelpFormatter(RawDescriptionHelpFormatter):
    """Public opt-out of colored --help (plain layout).

    Layout is produced by HelpRenderer. This class remains an argparse
    HelpFormatter so Meta.help_formatter and formatter_class identity stay
    valid.
    """

    config__max_help_position = MAX_HELP_POSITION

    def __init__(self, *args, max_help_position=None, **kwargs):
        super().__init__(
            *args, max_help_position=self.config__max_help_position, **kwargs
        )


class RichRecursiveHelpFormatter(RecursiveHelpFormatter):
    """Marker: same layout as ``RecursiveHelpFormatter``, with Rich color."""


class HelpRenderer:
    """Build and render --help from a ParserNode."""

    def __init__(self, node, colorizer: Optional[Callable] = None):
        self.node = node
        self.colorizer = colorizer

    def format_help(self, full: bool = False, topic: Optional[str] = None) -> str:
        """Help text, colorized when a colorizer is set.

        Short by default (collapsed groups summarized); ``full`` lists all.
        """
        doc = self.build(full=full, topic=topic)
        if self.colorizer is not None:
            return self.colorizer(doc)
        return doc.to_plain()

    def build(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self, full: bool = True, topic: Optional[str] = None
    ) -> HelpDocument:
        """Assemble the HelpDocument for this node."""
        node = self.node
        parser = node.parser
        layout = node.help_layout

        args = list(getattr(node, "help_args", None) or [])
        collapsed_titles = set(layout.collapsed_groups)
        hidden_items = [
            item
            for item in args
            if not item.is_hidden()
            and (item.advanced or item.group in collapsed_titles)
        ]
        flag = layout.help_all_flag
        if full or not hidden_items:
            hidden_items = []
        if getattr(node, "add_help", True):
            args = [_help_flag_arg()] + args
        if topic is not None:  # one group only: --help-<topic>
            hidden_items = []
            args = [item for item in args if item.group == topic]
        elif flag and (hidden_items or (full and _has_collapsible(args, layout))):
            args.insert(1 if getattr(node, "add_help", True) else 0, _help_all_arg(flag))
        visible = [
            item
            for item in args
            if not item.is_hidden() and not any(item is h for h in hidden_items)
        ]

        def arg_rows(items):
            return [(_format_invocation(item), _help_text_for(item)) for item in items]

        positionals = [i for i in visible if i.is_positional() and i.group is None]
        options = [i for i in visible if not i.is_positional() and i.group is None]
        groups: dict[str, list] = {}
        for item in visible:
            if item.group is not None:
                groups.setdefault(item.group, []).append(item)
        command_sections = [
            (title, _command_rows(members, layout))
            for title, members in _command_sections(node, layout)
        ]
        if topic is not None:
            command_sections = []
        sections = [
            ("positional arguments:", arg_rows(positionals), "cmds"),
            *((title, rows, "cmds") for title, rows in command_sections),
            ("options:", arg_rows(options), "args"),
            *(
                (f"{title}:", arg_rows(items), "args")
                for title, items in groups.items()
            ),
        ]

        labels = [label for _title, rows, _kind in sections for label, _help in rows]
        if node.children:
            labels.append("{" + ",".join(node.children) + "}")
        widths = _help_widths(max((len(label) for label in labels), default=0))

        doc = HelpDocument()
        for raw in parser.format_usage().rstrip("\n").splitlines() or [""]:
            if raw.startswith("usage:"):
                doc.add(("group", "usage:"), ("plain", raw[len("usage:") :]))
            else:
                doc.add(("plain", raw))
        description = strip_rst_literals(parser.description).rstrip("\n")
        if description:
            desc_lines = description.splitlines()
            if desc_lines[0] != "":
                doc.add()
            for raw in desc_lines:
                doc.add(("markup", raw))
        doc.add()

        for title, rows, kind in sections:
            if not rows:
                continue
            doc.add(("group", title))
            for label, help_msg in rows:
                _append_entry_lines(doc, label, help_msg, widths, name_kind=kind)
            doc.add()

        if hidden_items:
            summaries: dict[str, list] = {}
            for item in hidden_items:
                summaries.setdefault(item.group or "advanced options", []).append(item)
            for title, items in summaries.items():
                doc.add(
                    ("group", f"{title}:"),
                    ("plain", " " + _summarize(items, _help_width() - len(title) - 3)),
                )
            doc.add()
            topics = ", ".join(sorted({topic_flag(t) for t in summaries if t in collapsed_titles}))
            more = f" (or {topics} for one section)" if topics else ""
            doc.add(("plain", f"Use {flag} to list every option{more}."))
            doc.add()

        epilog = strip_rst_literals(parser.epilog).rstrip("\n")
        if epilog:
            for raw in epilog.splitlines():
                doc.add(("markup", raw))

        # One newline per line is added by to_plain: drop trailing blanks.
        while doc.lines and not doc.lines[-1].parts:
            doc.lines.pop()
        return doc


def _help_widths(max_label: int) -> _HelpWidths:
    indent = 2
    action_width = min(max_label + indent + 2, MAX_HELP_POSITION) - indent - 2
    if action_width < 1:
        action_width = max(max_label, 1)
    help_position = action_width + indent + 2
    return _HelpWidths(
        action_width=action_width,
        help_position=help_position,
        help_width=max(_help_width() - help_position, 11),
    )


def _help_width() -> int:
    width, _height = terminal_size()
    return max(width - 2, 40)


def topic_flag(title: str) -> str:
    """``--help-<slug>`` flag for an option group title."""
    slug = title.lower().removesuffix(" options").strip()
    slug = "".join(ch if ch.isalnum() else "-" for ch in slug).strip("-")
    return f"--help-{slug}"


def _has_collapsible(args, layout: HelpLayout) -> bool:
    titles = set(layout.collapsed_groups)
    return any(
        not item.is_hidden() and (item.advanced or item.group in titles)
        for item in args
    )


def _help_all_arg(flag: str) -> HelpArg:
    return HelpArg(
        dest="help_all",
        option_strings=(flag,),
        help="show all options, including output and parent options",
        default=SUPPRESS,
        nargs=0,
    )


def _summarize(items, width: int) -> str:
    """``--a, --b, ... (N options)`` clipped to *width* characters."""
    names = [
        next((o for o in item.option_strings if o.startswith("--")), None)
        or (item.option_strings[0] if item.option_strings else item.dest)
        for item in items
    ]
    tail = f" ({len(names)} options)"
    out = ""
    for idx, name in enumerate(names):
        sep = ", " if out else ""
        if len(out) + len(sep) + len(name) + len(tail) + 5 > width and idx:
            return out + ", ..." + tail
        out += sep + name
    return out + tail


def _help_flag_arg() -> HelpArg:
    return HelpArg(
        dest="help",
        option_strings=("-h", "--help"),
        help="show this help message and exit",
        default=SUPPRESS,
        nargs=0,
        suppress=False,
    )


def _format_args(item: HelpArg) -> str:
    metavar = item.metavar
    if metavar is None:
        if item.choices:
            metavar = "{" + ",".join(str(choice) for choice in item.choices) + "}"
        else:
            metavar = (item.dest or "").upper()
    if isinstance(metavar, tuple):
        metavar = " ".join(str(part) for part in metavar)
    nargs = item.nargs
    if nargs == OPTIONAL:
        return f"[{metavar}]"
    if nargs in (ZERO_OR_MORE, "*"):
        return f"[{metavar} [{metavar} ...]]"
    if nargs == "+":
        return f"{metavar} [{metavar} ...]"
    if nargs == "...":
        return "..."
    if isinstance(nargs, int) and nargs > 1:
        return " ".join([str(metavar)] * nargs)
    return str(metavar)


def _format_invocation(item: HelpArg) -> str:
    if not item.option_strings:
        if item.metavar:
            if isinstance(item.metavar, tuple):
                return " ".join(str(part) for part in item.metavar)
            return str(item.metavar)
        return (item.dest or "").upper()
    if item.nargs == 0:
        return ", ".join(item.option_strings)
    args_string = _format_args(item)
    return ", ".join(f"{opt} {args_string}" for opt in item.option_strings)


def _help_text_for(item: HelpArg) -> str:
    help_msg = strip_rst_literals(item.help)
    if "%(default)" not in help_msg and item.default is not SUPPRESS:
        defaulting = [OPTIONAL, ZERO_OR_MORE]
        if item.option_strings or item.nargs in defaulting:
            help_msg = f"{help_msg} (default: {item.default})".strip()
    return help_msg


def _append_entry_lines(
    doc: HelpDocument,
    invocation: str,
    help_msg: str,
    widths: _HelpWidths,
    name_kind: str,
) -> None:
    line = HelpLine()
    line.append("plain", "  ")
    line.append(name_kind, invocation)
    if not help_msg:
        doc.lines.append(line)
        return
    if len(invocation) > widths.action_width:
        doc.lines.append(line)
        wrapped = textwrap.wrap(help_msg, widths.help_width) or [""]
        for chunk in wrapped:
            wrap_line = HelpLine()
            wrap_line.append("plain", " " * widths.help_position)
            _append_help_with_default(wrap_line, chunk)
            doc.lines.append(wrap_line)
        return
    pad = " " * (widths.action_width - len(invocation))
    line.append("plain", pad + "  ")
    _append_help_with_default(line, help_msg)
    doc.lines.append(line)


def _append_help_with_default(line: HelpLine, help_msg: str) -> None:
    marker = "(default: "
    idx = help_msg.find(marker)
    if idx < 0:
        line.append("plain", help_msg)
        return
    line.append("plain", help_msg[:idx])
    line.append("default", help_msg[idx:])


def _nested_cmd_label(prefix: str, dest: str, hide_parent: bool, level: int) -> str:
    if hide_parent:
        return f"{HELP_NESTED_INDENT * level}{dest}"
    return f"{prefix}{dest}"


def _grouped_subcommand_sections(node, layout: HelpLayout):
    named_groups = layout.command_groups or ()
    named_titles = dict(named_groups)
    named_keys = [key for key, _title in named_groups]
    by_group: dict = {}
    for dest, child in node.children.items():
        group_key = getattr(child, "command_group", None)
        by_group.setdefault(group_key, []).append((dest, child))

    for key in named_keys:
        members = by_group.get(key)
        if members:
            yield named_titles[key], members

    unknown_keys = []
    for dest, child in node.children.items():
        group_key = getattr(child, "command_group", None)
        if group_key is None or group_key in named_titles:
            continue
        if group_key not in unknown_keys:
            unknown_keys.append(group_key)
    for key in unknown_keys:
        title = key if str(key).endswith(":") else f"{key}:"
        yield title, by_group.get(key)

    leftover = by_group.get(None)
    if leftover:
        yield "subcommands:", leftover


def _command_sections(node, layout: HelpLayout):
    """``(title, [(dest, child), ...])`` subcommand sections of *node*."""
    if not node.children:
        return []
    if not any(getattr(c, "command_group", None) for c in node.children.values()):
        return [("subcommands:", list(node.children.items()))]
    return list(_grouped_subcommand_sections(node, layout))


def _command_rows(members, layout: HelpLayout) -> list[tuple[str, str]]:
    """``(label, help)`` rows for *members*, plus nested ones when listing all."""
    rows = []
    list_nested = layout.subcommands == HELP_SUBCOMMANDS_ALL

    def add(dest, child, level, prefix):
        label = (
            dest
            if level == 0
            else _nested_cmd_label(prefix, dest, layout.hide_parent, level)
        )
        rows.append(
            (label, strip_rst_literals(getattr(child, "command_help", None) or ""))
        )
        if list_nested:
            for nested_dest, nested in child.children.items():
                add(nested_dest, nested, level + 1, f"{prefix}{dest} ")

    for dest, child in members:
        add(dest, child, 0, "")
    return rows


_HELP_STYLES = {
    "argparse.groups": "bold magenta",
    "argparse.args": "cyan",
    "argparse.cmds": "dark_cyan",
    "argparse.default": "dim",
}

_PART_STYLES = {
    "group": "argparse.groups",
    "args": "argparse.args",
    "cmds": "argparse.cmds",
    "default": "argparse.default",
}


def help_uses_rich() -> bool:
    """Whether ``--help`` should emit ANSI."""
    if not colors_enabled() or not stream_isatty(sys.stdout):
        return False
    return color_backend_uses_rich()


def help_document_colorizer(document: HelpDocument) -> str:
    """Style a HelpDocument. No regex on argparse text."""
    if not help_uses_rich():
        return document.to_plain()
    # Imported lazily: rich is slow to import and only needed for color.
    rich_console = optional("rich.console")
    rich_text = optional("rich.text")
    if rich_console is None or rich_text is None:
        return document.to_plain()
    Text = rich_text.Text  # pylint: disable=invalid-name
    styled = Text()
    max_len = 80
    for line in document.lines:
        line_text = "".join(text for _kind, text in line.parts)
        max_len = max(max_len, len(line_text))
        for kind, chunk in line.parts:
            if kind == "markup":
                rendered = render_markup_text(chunk)
                if rendered != chunk and hasattr(Text, "from_ansi"):
                    styled.append_text(Text.from_ansi(rendered))
                elif rendered != chunk:
                    styled.append(rendered)
                else:
                    try:
                        styled.append_text(Text.from_markup(chunk))
                    except Exception:  # pylint: disable=broad-exception-caught
                        styled.append(chunk)
            else:
                style = _PART_STYLES.get(kind)
                if style:
                    styled.append(chunk, style=style)
                else:
                    styled.append(chunk)
        styled.append("\n")
    console = make_rich_console(
        rich_console, width=max(max_len, 80), theme=_HELP_STYLES
    )
    with console.capture() as capture:
        console.print(styled, end="", overflow="ignore", crop=False, highlight=False)
    return capture.get()
