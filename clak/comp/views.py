"""View mixins for automatic CLI rendering and view options.

Option layers (mirror ClakView hierarchy):

1. ClakViewOptMixin — generic: ``width``
2. TableViewOptMixin — table (Show/List): ``format``, ``columns``,
   ``sort_columns``, ``sort_mode``, ``wrap``, ``add_index``
3. ListViewMixin — list-only: ``expand_keys``
4. TextViewOptMixin — text (Markdown/Rst): ``format`` (``view`` / ``raw``)
5. PprintViewMixin / RawViewMixin — enables only ``width``

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
    TEXT_FORMATS,
    WIDTH_MODES,
    WRAP_MODES,
    ListView,
    MarkdownView,
    PprintView,
    RawView,
    RstView,
    ShowView,
    normalize_columns,
    normalize_sort_columns,
    parse_columns,
    parse_sort_columns,
)

logger = logging.getLogger(__name__)

# Layer option dest sets (explicit unions avoid MRO drift)
_LAYER_GENERIC_DESTS = frozenset({"width"})
_LAYER_TABLE_DESTS = frozenset(
    {
        "format",
        "columns",
        "sort_columns",
        "sort_mode",
        "wrap",
        "add_index",
    }
)
_LAYER_LIST_DESTS = frozenset({"expand_keys"})
_LAYER_TEXT_DESTS = frozenset({"format"})

# All known view CLI dests (used to filter Argument collection)
_VIEW_CLI_OPTION_DESTS = (
    _LAYER_GENERIC_DESTS
    | _LAYER_TABLE_DESTS
    | _LAYER_LIST_DESTS
    | _LAYER_TEXT_DESTS
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
    "View width mode: min (content-sized), auto (wrap if wider than "
    "terminal), terminal (always terminal width). No wrap when stdout "
    "is not a TTY."
)
_WRAP_HELP = (
    "Table column wrap when fitting to terminal: last (rightmost "
    "column only), all (any column). Ignored when width is min or "
    "stdout is not a TTY."
)
_FORMAT_HELP = "Output format (default: view table)"
_TEXT_FORMAT_HELP = (
    "Output format: view (rendered) or raw (source). Default: view"
)
_SORT_MODE_HELP = "Sort direction (default: asc)"
_ADD_INDEX_HELP = "Include key/index column in the table"
_EXPAND_KEYS_HELP = "Expand nested dict items into table columns"


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
            if key in ("columns", "sort_columns"):
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

        for key in ("add_index", "expand_keys", "width", "wrap", "format", "sort_mode"):
            if key not in enabled:
                continue
            value = self._args_get(args, key, None)
            if value is not None:
                settings[key] = value

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
            ("width", "view_width", None),
            ("wrap", "view_wrap", None),
            ("format", "view_format", None),
            ("add_index", "view_add_index", None),
            ("expand_keys", "view_expand_keys", None),
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
    """Layer 1: generic ClakView output options (``width``)."""

    _view_cli_option_names = _LAYER_GENERIC_DESTS

    meta__config__view_width = MetaSetting(
        help="Default view width mode: min, auto, or terminal",
    )
    meta__view_width = None

    width = Argument(
        "--width",
        choices=sorted(WIDTH_MODES),
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_WIDTH_HELP,
    )


class TableViewOptMixin(ClakViewOptMixin):
    """Layer 2: table view options shared by Show and List."""

    _view_cli_option_names = _LAYER_GENERIC_DESTS | _LAYER_TABLE_DESTS

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
        help="Default table wrap mode: last or all",
    )
    meta__view_wrap = None

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
        group=_OUTPUT_OPTIONS_GROUP,
        help=_COLUMNS_HELP,
    )
    add_index = Argument(
        "--add-index",
        action=argparse.BooleanOptionalAction,
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_ADD_INDEX_HELP,
    )
    format = Argument(
        "--format",
        choices=["view", "yaml", "json", "csv"],
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_FORMAT_HELP,
    )
    sort_columns = Argument(
        "--sort-columns",
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_SORT_COLUMNS_HELP,
    )
    sort_mode = Argument(
        "--sort-mode",
        choices=["asc", "desc"],
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_SORT_MODE_HELP,
    )
    wrap = Argument(
        "--wrap",
        choices=sorted(WRAP_MODES),
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_WRAP_HELP,
    )


class ShowViewMixin(TableViewOptMixin):
    """Auto-render command results with :class:`~clak.views.ShowView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--format``, ``--sort-columns``, ``--sort-mode``, ``--width``,
    and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_GENERIC_DESTS | _LAYER_TABLE_DESTS
    meta__cli_view = ShowView


class ListViewMixin(TableViewOptMixin):
    """Auto-render command results with :class:`~clak.views.ListView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--expand-keys`` / ``--no-expand-keys``, ``--format``,
    ``--sort-columns``, ``--sort-mode``, ``--width``, and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = (
        _LAYER_GENERIC_DESTS | _LAYER_TABLE_DESTS | _LAYER_LIST_DESTS
    )
    meta__cli_view = ListView

    meta__config__view_expand_keys = MetaSetting(
        help="Default for --expand-keys / --no-expand-keys",
    )
    meta__view_expand_keys = None

    expand_keys = Argument(
        "--expand-keys",
        action=argparse.BooleanOptionalAction,
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_EXPAND_KEYS_HELP,
    )


class PprintViewMixin(ClakViewOptMixin):
    """Auto-render command results with :class:`~clak.views.PprintView`.

    Adds ``--width``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_GENERIC_DESTS
    meta__cli_view = PprintView


class TextViewOptMixin(ClakViewOptMixin):
    """Layer 2: text view options shared by Markdown and Rst."""

    _view_cli_option_names = _LAYER_GENERIC_DESTS | _LAYER_TEXT_DESTS

    meta__config__view_format = MetaSetting(
        help="Default output format: view (rendered) or raw (source)",
    )
    meta__view_format = None

    format = Argument(
        "--format",
        choices=sorted(TEXT_FORMATS),
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_TEXT_FORMAT_HELP,
    )


class RawViewMixin(ClakViewOptMixin):
    """Auto-render command results with :class:`~clak.views.RawView`.

    Adds ``--width``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_GENERIC_DESTS
    meta__cli_view = RawView


class MarkdownViewMixin(TextViewOptMixin):
    """Auto-render command results with :class:`~clak.views.MarkdownView`.

    Adds ``--format`` (``view`` / ``raw``) and ``--width``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_GENERIC_DESTS | _LAYER_TEXT_DESTS
    meta__cli_view = MarkdownView


class RstViewMixin(TextViewOptMixin):
    """Auto-render command results with :class:`~clak.views.RstView`.

    Adds ``--format`` (``view`` / ``raw``) and ``--width``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = _LAYER_GENERIC_DESTS | _LAYER_TEXT_DESTS
    meta__cli_view = RstView
