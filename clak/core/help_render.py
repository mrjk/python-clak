"""Clak-owned --help layout (not an argparse HelpFormatter).

Walks ParserNode / HelpArg records. Does not regex argparse output.
"""

from __future__ import annotations

import os
import shutil
import textwrap
from argparse import OPTIONAL, SUPPRESS, ZERO_OR_MORE, RawDescriptionHelpFormatter
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

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

    @classmethod
    def from_action(cls, action, group=None) -> "HelpArg":
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
        )

    def is_positional(self) -> bool:
        return not self.option_strings

    def is_hidden(self) -> bool:
        return self.suppress or (self.dest or "").startswith("__")


@dataclass
class HelpLine:
    """One output line as typed parts (kind, text)."""

    parts: list[tuple[str, str]] = field(default_factory=list)

    def append(self, kind: str, text: str) -> None:
        if text:
            self.parts.append((kind, text))


@dataclass
class HelpDocument:
    """Structured help; render to plain text or styled parts."""

    lines: list[HelpLine] = field(default_factory=list)
    usage_lines: list[HelpLine] = field(default_factory=list)

    def to_plain(self, *, usage_only: bool = False) -> str:
        rows = self.usage_lines if usage_only else self.lines
        chunks = []
        for line in rows:
            chunks.append("".join(text for _kind, text in line.parts))
            chunks.append("\n")
        return "".join(chunks)


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


def help_layout_for(node) -> HelpLayout:
    """Layout stored on the node, or defaults."""
    layout = getattr(node, "help_layout", None)
    if layout is None:
        return HelpLayout()
    return layout


class HelpRenderer:
    """Build and render --help from a ParserNode."""

    def __init__(self, node, colorizer: Optional[Callable] = None):
        self.node = node
        self.colorizer = colorizer

    def format_usage(self) -> str:
        doc = self.build()
        return doc.to_plain(usage_only=True)

    def format_help(self) -> str:
        doc = self.build()
        if self.colorizer is not None:
            return self.colorizer(doc)
        return doc.to_plain()

    def build(
        self,
    ) -> (
        HelpDocument
    ):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        node = self.node
        parser = node.parser
        width = _help_width()
        args = list(getattr(node, "help_args", None) or [])
        if getattr(node, "add_help", True):
            args = [_help_flag_arg()] + args

        layout = help_layout_for(node)
        invocations = {}
        visible = [item for item in args if not item.is_hidden()]
        for item in visible:
            invocations[id(item)] = _format_invocation(item)

        cmd_labels = _collect_command_labels(node, layout)
        max_inv = 0
        if invocations:
            max_inv = max(len(text) for text in invocations.values())
        if cmd_labels:
            max_inv = max(max_inv, max(len(label) for label in cmd_labels))
        if node.children:
            max_inv = max(max_inv, len("{%s}" % ",".join(node.children)))
        indent = 2
        help_position = min(max_inv + indent + 2, MAX_HELP_POSITION)
        action_width = help_position - indent - 2
        if action_width < 1:
            action_width = max(max_inv, 1)
        help_position = action_width + indent + 2
        help_width = max(width - help_position, 11)

        doc = HelpDocument()
        usage_text = parser.format_usage().rstrip("\n")
        for raw in usage_text.splitlines() or [""]:
            usage_line = HelpLine()
            if raw.startswith("usage:"):
                usage_line.append("group", "usage:")
                usage_line.append("plain", raw[len("usage:") :])
            else:
                usage_line.append("plain", raw)
            doc.usage_lines.append(usage_line)
            doc.lines.append(usage_line)
        description = strip_rst_literals(parser.description).rstrip("\n")
        if description:
            desc_lines = description.splitlines() or [""]
            if desc_lines[0] != "":
                doc.lines.append(HelpLine())
            for raw in desc_lines:
                line = HelpLine()
                line.append("markup", raw)
                doc.lines.append(line)
            doc.lines.append(HelpLine())
        else:
            doc.lines.append(HelpLine())

        positionals = [
            item for item in visible if item.is_positional() and item.group is None
        ]
        ungrouped_opts = [
            item
            for item in visible
            if (not item.is_positional()) and item.group is None
        ]
        extra_groups: list[str] = []
        grouped: dict[str, list] = {}
        for item in visible:
            if item.group is None:
                continue
            if item.group not in grouped:
                extra_groups.append(item.group)
                grouped[item.group] = []
            grouped[item.group].append(item)

        def add_section(title: str, items: list, kind: str) -> None:
            if not items:
                return
            heading = HelpLine()
            heading.append("group", title)
            doc.lines.append(heading)
            for item in items:
                _append_entry_lines(
                    doc,
                    invocations[id(item)],
                    _help_text_for(item),
                    action_width,
                    help_position,
                    help_width,
                    name_kind=kind,
                )
            doc.lines.append(HelpLine())

        add_section("positional arguments:", positionals, "cmds")
        _append_subcommand_sections(
            doc, node, layout, action_width, help_position, help_width
        )
        add_section("options:", ungrouped_opts, "args")
        for title in extra_groups:
            add_section(f"{title}:", grouped[title], "args")

        epilog = strip_rst_literals(parser.epilog).rstrip("\n")
        if epilog:
            for raw in epilog.splitlines() or [""]:
                line = HelpLine()
                line.append("markup", raw)
                doc.lines.append(line)
            doc.lines.append(HelpLine())

        # argparse format_help ends with a trailing newline after last content;
        # we already add newline per line. Drop a surplus empty tail if epilog
        # already provided the blank. Keep one trailing newline via to_plain.
        while doc.lines and not doc.lines[-1].parts:
            doc.lines.pop()
        return doc


def _help_width() -> int:
    try:
        width = int(os.environ["COLUMNS"])
    except (KeyError, ValueError):
        width = shutil.get_terminal_size().columns
    return max(width - 2, 40)


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
            metavar = "{%s}" % ",".join(str(choice) for choice in item.choices)
        else:
            metavar = (item.dest or "").upper()
    if isinstance(metavar, tuple):
        metavar = " ".join(str(part) for part in metavar)
    nargs = item.nargs
    if nargs is None or nargs == 0:
        return str(metavar)
    if nargs == OPTIONAL:
        return "[%s]" % metavar
    if nargs == ZERO_OR_MORE:
        return "[%s [%s ...]]" % (metavar, metavar)
    if nargs == "*":
        return "[%s [%s ...]]" % (metavar, metavar)
    if nargs == "+":
        return "%s [%s ...]" % (metavar, metavar)
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
    action_width: int,
    help_position: int,
    help_width: int,
    name_kind: str,
    prefix: str = "  ",
) -> None:
    line = HelpLine()
    line.append("plain", prefix)
    line.append(name_kind, invocation)
    if not help_msg:
        doc.lines.append(line)
        return
    if len(invocation) > action_width:
        doc.lines.append(line)
        wrapped = textwrap.wrap(help_msg, help_width) or [""]
        for chunk in wrapped:
            wrap_line = HelpLine()
            wrap_line.append("plain", " " * help_position)
            _append_help_with_default(wrap_line, chunk)
            doc.lines.append(wrap_line)
        return
    pad = " " * (action_width - len(invocation))
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


def _collect_command_labels(node, layout: HelpLayout) -> list[str]:
    labels = []
    list_nested = layout.subcommands == HELP_SUBCOMMANDS_ALL
    hide_parent = layout.hide_parent

    def walk(current, prefix: str, level: int) -> None:
        for dest, child in current.children.items():
            if getattr(child, "command_help_suppress", False):
                continue
            labels.append(_nested_cmd_label(prefix, dest, hide_parent, level))
            if list_nested:
                walk(child, f"{prefix}{dest} ", level + 1)

    for dest in node.children:
        labels.append(dest)
        if list_nested:
            walk(node.children[dest], f"{dest} ", 1)
    return labels


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


def _append_subcommand_sections(
    doc, node, layout, action_width, help_position, help_width
):
    if not node.children:
        return
    list_nested = layout.subcommands == HELP_SUBCOMMANDS_ALL
    hide_parent = layout.hide_parent
    grouped = any(
        getattr(child, "command_group", None) for child in node.children.values()
    )

    def add_choice(dest, child, level=0, prefix=""):
        help_msg = strip_rst_literals(getattr(child, "command_help", None) or "")
        label = (
            dest if level == 0 else _nested_cmd_label(prefix, dest, hide_parent, level)
        )
        _append_entry_lines(
            doc,
            label,
            help_msg,
            action_width,
            help_position,
            help_width,
            name_kind="cmds",
        )
        if list_nested and child.children:
            for nested_dest, nested in child.children.items():
                add_choice(
                    nested_dest,
                    nested,
                    level=level + 1,
                    prefix=f"{prefix}{dest} " if prefix or level else f"{dest} ",
                )

    if not grouped:
        heading = HelpLine()
        heading.append("group", "subcommands:")
        doc.lines.append(heading)
        for dest, child in node.children.items():
            add_choice(dest, child)
        doc.lines.append(HelpLine())
        return

    for title, members in _grouped_subcommand_sections(node, layout):
        heading = HelpLine()
        heading.append("group", title)
        doc.lines.append(heading)
        for dest, child in members:
            add_choice(dest, child)
        doc.lines.append(HelpLine())
