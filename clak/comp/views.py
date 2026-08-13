"""View mixins for automatic CLI rendering and view options.

Option layers (mirror ClakView hierarchy):

1. ClakViewOptMixin — generic (no CLI flags)
2. TableViewOptMixin — table (Show/List): ``width``, ``format``, ``columns``,
   ``sort_columns``, ``sort_mode``, ``wrap``, ``add_index``
3. ListViewMixin — list-only: ``expand_keys``
4. TextLayoutOptMixin — text wrap: ``line_length``
5. TextViewOptMixin — text (Markdown/Rst): ``format`` (``view`` / ``raw``)
   plus ``line_length``
6. PprintViewMixin / RawViewMixin — ``line_length`` only
7. DataViewMixin — structured dump: ``format``, ``compact``, ``color``,
   ``anchors``
8. CompositeViewMixin — table opts + ``expand_keys`` + ``format_scope`` +
   ``line_length`` (return a ``CompositeView``; no auto ``cli_view``)

Example:

    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = True  # or False, or ("columns", "add_index")
            view_columns = ("name", "role")
            view_column_names = ("name", "role", "city")
            view_sort_columns = 1
            view_format = "view"
            view_width = "terminal"
            view_wrap = "last"

        def cli_run(self, **_):
            return [{"name": "a"}, {"name": "b"}]
"""

# pylint: disable=too-few-public-methods,duplicate-code

from __future__ import annotations

import argparse
import copy
import logging
from typing import Any, Mapping, Set

from clak.parser import Argument, MetaSetting
from clak.plugins import PluginHelpers
from clak.views import (
    DATA_FORMATS,
    FORMAT_SCOPES,
    TEXT_FORMATS,
    WIDTH_MODES,
    DataView,
    ListView,
    MarkdownView,
    PprintView,
    RawView,
    RstView,
    ShowView,
    normalize_columns,
    normalize_sort_columns,
    normalize_width_mode,
    normalize_wrap,
    normalize_wrap_min,
    parse_columns,
    parse_line_length,
    parse_sort_columns,
    parse_wrap,
)

logger = logging.getLogger(__name__)

# Layer option dest sets (explicit unions avoid MRO drift)
_LAYER_TABLE_DESTS = frozenset(
    {
        "width",
        "format",
        "columns",
        "sort_columns",
        "sort_mode",
        "wrap",
        "add_index",
    }
)
_LAYER_LIST_DESTS = frozenset({"expand_keys"})
_LAYER_TEXT_LAYOUT_DESTS = frozenset({"line_length"})
_LAYER_TEXT_DESTS = frozenset({"format"})
_LAYER_DATA_DESTS = frozenset({"format", "compact", "color", "anchors"})
_LAYER_COMPOSITE_DESTS = frozenset({"format_scope"})

# All known view CLI dests (used to filter Argument collection)
_VIEW_CLI_OPTION_DESTS = (
    _LAYER_TABLE_DESTS
    | _LAYER_LIST_DESTS
    | _LAYER_TEXT_LAYOUT_DESTS
    | _LAYER_TEXT_DESTS
    | _LAYER_DATA_DESTS
    | _LAYER_COMPOSITE_DESTS
)

_OUTPUT_OPTIONS_GROUP = "Output options"

_COLUMNS_HELP = (
    "Comma-separated columns to display (names, 1-based indexes, "
    "or negatives from end: -1=last)"
)
_SORT_COLUMNS_HELP = (
    "Comma-separated columns to sort by (names, 1-based indexes, "
    "or negatives from end: -1=last). Use --sort-columns=-1,1 when "
    "values start with '-'."
)
_WIDTH_HELP = (
    "Table width: content (size to data), fit (shrink if wider than "
    "terminal), terminal (use terminal width). No wrap when stdout "
    "is not a TTY."
)
_WRAP_HELP = (
    "Flexible table columns: they expand or shrink to the terminal. "
    "last (rightmost), first (leftmost), all (any column), or "
    "comma-separated names/indexes in priority order. Use --wrap=-1 "
    "when the value starts with '-'. Ignored when width is content or "
    "stdout is not a TTY."
)
_LINE_LENGTH_HELP = (
    "Wrap text at N columns (default 120), terminal, or nowrap. "
    "No wrap when stdout is not a TTY."
)
_FORMAT_HELP = "Output format (default: view table)"
_TEXT_FORMAT_HELP = "Output format: view (rendered) or raw (source). Default: view"
_DATA_FORMAT_HELP = (
    "Output format: json or yaml. Default: yaml when PyYAML is installed, else json"
)
_COMPACT_HELP = "Compact JSON (single line). Ignored for YAML. Default: off"
_COLOR_HELP = (
    "Colorize JSON/YAML with rich when available. Default: on for TTY "
    + "when CLAK_COLORS is enabled"
)
_ANCHORS_HELP = (
    "Allow YAML anchors/aliases for shared references. Ignored for JSON. "
    + "Default: on"
)
_SORT_MODE_HELP = "Sort direction (default: asc)"
_ADD_INDEX_HELP = "Include key/index column in the table"
_EXPAND_KEYS_HELP = "Expand nested dict items into table columns"
_FORMAT_SCOPE_HELP = (
    "When using CompositeView with machine formats: first (primary "
    "section only) or all (envelope of every section). Default: first"
)


class _ViewMixinBase(PluginHelpers):
    """Shared view-mixin plumbing: option filtering, hook, settings collection."""

    _view_cli_option_names: frozenset[str] = frozenset()

    meta__config__view_cli_options = MetaSetting(
        help=(
            "Which view CLI options to expose: True (all), False (none), "
            "or a sequence of option names"
        ),
    )
    meta__view_cli_options = True

    def _enabled_view_options(self) -> Set[str]:
        available = set(self._view_cli_option_names)
        configured = self.query_cfg_parents(
            "view_cli_options", default=True, include_self=True
        )
        if configured is True:
            return available
        if configured is False:
            return set()
        if isinstance(configured, (list, tuple, set, frozenset)):
            requested = set(configured)
            unknown = requested - available
            if unknown:
                raise ValueError(
                    f"Unknown view_cli_options {sorted(unknown)}, "
                    f"available: {sorted(available)}"
                )
            return requested
        raise TypeError(
            "view_cli_options must be True, False, or a sequence of names, "
            f"got {type(configured).__name__}"
        )

    def _column_flag_help(self, base_help: str) -> str:
        """Append Available: names from Meta.view_column_names when configured."""
        names = self.query_cfg_parents(
            "view_column_names", default=None, include_self=True
        )
        if not names:
            return base_help
        available = ", ".join(str(name) for name in names)
        base = base_help.rstrip()
        if base.endswith("."):
            return f"{base} Available: {available}"
        return f"{base}. Available: {available}"

    def add_arguments(self, arguments: dict = None):
        """Like ParserNode.add_arguments, but skips disabled view CLI options."""
        arguments = dict(arguments or getattr(self, "meta__arguments_dict", {}) or {})
        if not isinstance(arguments, dict):
            raise TypeError(f"Got {type(arguments)} instead of dict")

        enabled = self._enabled_view_options()
        skip = _VIEW_CLI_OPTION_DESTS - enabled

        for cls in self.__class__.__mro__:
            for name, value in vars(cls).items():
                if isinstance(value, Argument) and name not in arguments:
                    if name in skip:
                        continue
                    value.destination = name
                    arguments[name] = value

        arguments["__cli_self__"] = Argument(help=argparse.SUPPRESS, default=self)

        for key, arg in arguments.items():
            if key in ("columns", "sort_columns", "wrap"):
                arg = copy.copy(arg)
                arg.kwargs = dict(arg.kwargs)
                arg.kwargs["help"] = self._column_flag_help(arg.kwargs.get("help", ""))
            self.add_argument(key, arg)

    @staticmethod
    def _args_get(args: Any, key: str, default=None):
        if isinstance(args, Mapping):
            return args.get(key, default)
        return getattr(args, key, default)

    def _collect_enabled_cli_settings(self, args: Any, enabled: Set[str]) -> dict:
        """Collect set CLI view flags into a settings dict."""
        settings: dict = {}

        if "columns" in enabled:
            raw = self._args_get(args, "columns", None)
            if raw is not None:
                settings["columns"] = parse_columns(raw)

        for key in (
            "add_index",
            "expand_keys",
            "width",
            "format",
            "format_scope",
            "sort_mode",
            "line_length",
            "compact",
            "color",
            "anchors",
        ):
            if key not in enabled:
                continue
            value = self._args_get(args, key, None)
            if value is not None:
                settings[key] = value

        if "wrap" in enabled:
            raw = self._args_get(args, "wrap", None)
            if raw is not None:
                settings["wrap"] = parse_wrap(raw)

        if "sort_columns" in enabled:
            raw = self._args_get(args, "sort_columns", None)
            if raw is not None:
                settings["sort_columns"] = parse_sort_columns(raw)

        return settings

    def _apply_meta_view_defaults(
        self, settings: dict, enabled: Set[str] | None = None
    ) -> None:
        """Fill unset settings from Meta.view_* defaults (enabled options only)."""
        meta_defaults = (
            ("columns", "view_columns", normalize_columns),
            ("sort_columns", "view_sort_columns", normalize_sort_columns),
            ("sort_mode", "view_sort_mode", None),
            ("width", "view_width", normalize_width_mode),
            ("line_length", "view_line_length", parse_line_length),
            ("wrap", "view_wrap", normalize_wrap),
            ("format", "view_format", None),
            ("format_scope", "view_format_scope", None),
            ("add_index", "view_add_index", None),
            ("expand_keys", "view_expand_keys", None),
            ("compact", "view_compact", None),
            ("color", "view_color", None),
            ("anchors", "view_anchors", None),
        )
        for key, meta_name, normalizer in meta_defaults:
            if enabled is not None and key not in enabled:
                continue
            if key in settings:
                continue
            value = self.query_cfg_parents(meta_name, default=None, include_self=True)
            if value is None:
                continue
            settings[key] = normalizer(value) if normalizer else value

        if "wrap" in self._view_cli_option_names and "wrap_min" not in settings:
            value = self.query_cfg_parents(
                "view_wrap_min", default=None, include_self=True
            )
            if value is not None:
                settings["wrap_min"] = normalize_wrap_min(value)

        if getattr(self, "_uses_syntax_theme", False) and "theme" not in settings:
            value = self.query_cfg_parents(
                "view_syntax_theme", default=None, include_self=True
            )
            if value is not None:
                settings["theme"] = value

    def collect_view_settings(self, args: Any) -> dict:
        """Build view render kwargs from parsed CLI args (only set flags)."""
        enabled = self._enabled_view_options()
        settings = self._collect_enabled_cli_settings(args, enabled)
        self._apply_meta_view_defaults(settings, enabled)
        return settings

    def cli_hook__views(self, instance, ctx, **_):  # pylint: disable=unused-argument
        "Collect view CLI options into ctx.plugins and stash on root for dispatch."
        settings = self.collect_view_settings(ctx.args)
        runtime = getattr(ctx, "runtime", None)
        if runtime is not None:
            runtime.get_size()
            settings["term_width"] = runtime.term_width
            settings["stdout_tty"] = runtime.stdout_tty
        ctx.plugins["view_settings"] = settings
        setattr(ctx.cli_root, "_clak_view_settings", settings)
        logger.debug("View settings for %s: %s", instance, settings)


class ClakViewOptMixin(_ViewMixinBase):
    """Layer 1: generic ClakView (no CLI flags)."""

    _view_cli_option_names = frozenset()


class TableViewOptMixin(ClakViewOptMixin):
    """Layer 2: table view options shared by Show and List."""

    _view_cli_option_names = _LAYER_TABLE_DESTS

    meta__config__view_width = MetaSetting(
        help="Default table width: content, fit, or terminal",
    )
    meta__view_width = None

    width = Argument(
        "--width",
        choices=sorted(WIDTH_MODES),
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_WIDTH_HELP,
    )

    meta__config__view_columns = MetaSetting(
        help=(
            "Default columns when --columns is unset "
            "(string, int index, or sequence; same syntax as --columns)"
        ),
    )
    meta__view_columns = None

    meta__config__view_column_names = MetaSetting(
        help=(
            "Full set of selectable column names shown in --columns / "
            "--sort-columns help (view_columns remains the default display subset)"
        ),
    )
    meta__view_column_names = None

    meta__config__view_sort_columns = MetaSetting(
        help=(
            "Default sort columns when --sort-columns is unset "
            "(string, int index, or sequence; same syntax as --sort-columns)"
        ),
    )
    meta__view_sort_columns = None

    meta__config__view_sort_mode = MetaSetting(
        help="Default sort mode: asc or desc",
    )
    meta__view_sort_mode = None

    meta__config__view_wrap = MetaSetting(
        help=(
            "Flexible table columns: last, first, all, or column "
            "names/indexes (same syntax as --columns)"
        ),
    )
    meta__view_wrap = None

    meta__config__view_wrap_min = MetaSetting(
        help=(
            "Shrink floor for flexible columns: positive int (all of them) "
            "or mapping of column spec to positive int"
        ),
    )
    meta__view_wrap_min = None

    meta__config__view_format = MetaSetting(
        help="Default output format: view, yaml, json, or csv",
    )
    meta__view_format = None

    meta__config__view_add_index = MetaSetting(
        help="Default for --add-index / --no-add-index",
    )
    meta__view_add_index = None

    columns = Argument(
        "--columns",
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_COLUMNS_HELP,
    )
    add_index = Argument(
        "--add-index",
        action=argparse.BooleanOptionalAction,
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_ADD_INDEX_HELP,
    )
    format = Argument(
        "--format",
        choices=["view", "yaml", "json", "csv"],
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_FORMAT_HELP,
    )
    sort_columns = Argument(
        "--sort-columns",
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_SORT_COLUMNS_HELP,
    )
    sort_mode = Argument(
        "--sort-mode",
        choices=["asc", "desc"],
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_SORT_MODE_HELP,
    )
    wrap = Argument(
        "--wrap",
        default=None,
        metavar="MODE|COL,...",
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_WRAP_HELP,
    )


class ShowViewMixin(TableViewOptMixin):
    """Auto-render command results with :class:`~clak.views.ShowView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--format``, ``--sort-columns``, ``--sort-mode``, ``--width``,
    and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_TABLE_DESTS
    meta__cli_view = ShowView


class ListViewMixin(TableViewOptMixin):
    """Auto-render command results with :class:`~clak.views.ListView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--expand-keys`` / ``--no-expand-keys``, ``--format``,
    ``--sort-columns``, ``--sort-mode``, ``--width``, and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_TABLE_DESTS | _LAYER_LIST_DESTS
    meta__cli_view = ListView

    meta__config__view_expand_keys = MetaSetting(
        help="Default for --expand-keys / --no-expand-keys",
    )
    meta__view_expand_keys = None

    expand_keys = Argument(
        "--expand-keys",
        action=argparse.BooleanOptionalAction,
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_EXPAND_KEYS_HELP,
    )


class TextLayoutOptMixin(ClakViewOptMixin):
    """Text wrap options shared by Raw, Pprint, Markdown, Rst, and Composite."""

    _view_cli_option_names = _LAYER_TEXT_LAYOUT_DESTS

    meta__config__view_line_length = MetaSetting(
        help="Default text wrap: positive int, terminal, or nowrap",
    )
    meta__view_line_length = None

    line_length = Argument(
        "--line-length",
        type=parse_line_length,
        default=None,
        metavar="N|terminal|nowrap",
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_LINE_LENGTH_HELP,
    )


class PprintViewMixin(TextLayoutOptMixin):
    """Auto-render command results with :class:`~clak.views.PprintView`.

    Adds ``--line-length``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_TEXT_LAYOUT_DESTS
    meta__cli_view = PprintView


class TextViewOptMixin(TextLayoutOptMixin):
    """Layer 2: text view options shared by Markdown and Rst."""

    _view_cli_option_names = _LAYER_TEXT_LAYOUT_DESTS | _LAYER_TEXT_DESTS

    meta__config__view_format = MetaSetting(
        help="Default output format: view (rendered) or raw (source)",
    )
    meta__view_format = None

    format = Argument(
        "--format",
        choices=sorted(TEXT_FORMATS),
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_TEXT_FORMAT_HELP,
    )


class RawViewMixin(TextLayoutOptMixin):
    """Auto-render command results with :class:`~clak.views.RawView`.

    Adds ``--line-length``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_TEXT_LAYOUT_DESTS
    meta__cli_view = RawView


class MarkdownViewMixin(TextViewOptMixin):
    """Auto-render command results with :class:`~clak.views.MarkdownView`.

    Adds ``--format`` (``view`` / ``raw``) and ``--line-length``.
    Syntax theme: ``Meta.view_syntax_theme`` or ``CLAK_SYNTAX_THEME``, else
    ``ansi_dark``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_TEXT_LAYOUT_DESTS | _LAYER_TEXT_DESTS
    _uses_syntax_theme = True
    meta__cli_view = MarkdownView

    meta__config__view_syntax_theme = MetaSetting(
        help=(
            "Pygments/Rich Syntax theme for markdown code fences. "
            "Overrides CLAK_SYNTAX_THEME; default ansi_dark"
        ),
    )
    meta__view_syntax_theme = None


class RstViewMixin(TextViewOptMixin):
    """Auto-render command results with :class:`~clak.views.RstView`.

    Adds ``--format`` (``view`` / ``raw``) and ``--line-length``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_TEXT_LAYOUT_DESTS | _LAYER_TEXT_DESTS
    meta__cli_view = RstView


class DataViewMixin(_ViewMixinBase):
    """Auto-render command results with :class:`~clak.views.DataView`.

    Adds ``--format`` (``json`` / ``yaml``), ``--compact`` / ``--no-compact``,
    ``--color`` / ``--no-color``, and ``--anchors`` / ``--no-anchors``.
    Syntax theme: ``Meta.view_syntax_theme`` or ``CLAK_SYNTAX_THEME``, else
    ``ansi_dark``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_DATA_DESTS
    _uses_syntax_theme = True
    meta__cli_view = DataView

    meta__config__view_format = MetaSetting(
        help="Default data format: json, yaml, or unset for auto",
    )
    meta__view_format = None

    meta__config__view_compact = MetaSetting(
        help="Default for --compact / --no-compact (JSON only)",
    )
    meta__view_compact = None

    meta__config__view_color = MetaSetting(
        help="Default for --color / --no-color",
    )
    meta__view_color = None

    meta__config__view_anchors = MetaSetting(
        help="Default for --anchors / --no-anchors (YAML only)",
    )
    meta__view_anchors = None

    meta__config__view_syntax_theme = MetaSetting(
        help=(
            "Pygments/Rich Syntax theme for DataView and Markdown code. "
            "Overrides CLAK_SYNTAX_THEME; default ansi_dark"
        ),
    )
    meta__view_syntax_theme = None

    format = Argument(
        "--format",
        choices=sorted(DATA_FORMATS),
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_DATA_FORMAT_HELP,
    )

    compact = Argument(
        "--compact",
        action=argparse.BooleanOptionalAction,
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_COMPACT_HELP,
    )

    color = Argument(
        "--color",
        action=argparse.BooleanOptionalAction,
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_COLOR_HELP,
    )

    anchors = Argument(
        "--anchors",
        action=argparse.BooleanOptionalAction,
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_ANCHORS_HELP,
    )


class CompositeViewMixin(TextLayoutOptMixin, TableViewOptMixin):
    """CLI flags for multi-section :class:`~clak.views.CompositeView` output.

    Adds table options, ``--expand-keys``, ``--format-scope``, ``--width``,
    and ``--line-length``. Does **not** set ``Meta.cli_view``: return a
    ``CompositeView(...)`` from ``cli_run``. Table flags apply to the primary
    section only. ``--line-length`` applies to text/pprint sections only.
    ``--expand-keys`` is for a ListView primary; hide it with
    ``Meta.view_cli_options`` when the primary is ShowView.
    ``--format`` is table-scoped (``view`` / ``yaml`` / ``json`` / ``csv``);
    markdown source is in ``--format-scope all`` envelopes, not ``--format raw``.
    """

    _view_cli_option_names = (
        _LAYER_TABLE_DESTS
        | _LAYER_LIST_DESTS
        | _LAYER_COMPOSITE_DESTS
        | _LAYER_TEXT_LAYOUT_DESTS
    )

    meta__config__view_format_scope = MetaSetting(
        help="Default format scope for CompositeView: first or all",
    )
    meta__view_format_scope = None

    meta__config__view_expand_keys = MetaSetting(
        help="Default for --expand-keys / --no-expand-keys",
    )
    meta__view_expand_keys = None

    expand_keys = Argument(
        "--expand-keys",
        action=argparse.BooleanOptionalAction,
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_EXPAND_KEYS_HELP,
    )
    format_scope = Argument(
        "--format-scope",
        choices=sorted(FORMAT_SCOPES),
        default=None,
        option_group=_OUTPUT_OPTIONS_GROUP,
        help=_FORMAT_SCOPE_HELP,
    )
