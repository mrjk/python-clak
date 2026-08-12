"""View mixins for automatic CLI rendering and view options.

Mix in one of:
- ShowViewMixin → ShowView + --columns / --add-index / --format /
  --sort-columns / --width / --wrap
- ListViewMixin → ListView + --columns / --add-index / --expand-keys /
  --format / --sort-columns / --width / --wrap
- PprintViewMixin → PprintView + --width

Example:

    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = True  # or False, or ("columns", "add_index")
            view_columns = ("name", "role")
            view_column_names = ("name", "role", "city")
            view_sort_columns = 1
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
    WIDTH_MODES,
    WRAP_MODES,
    ListView,
    PprintView,
    ShowView,
    normalize_columns,
    normalize_sort_columns,
    parse_columns,
    parse_sort_columns,
)

logger = logging.getLogger(__name__)

# Destination names shared across view mixins (used to filter Argument collection)
_VIEW_CLI_OPTION_DESTS = frozenset(
    {
        "columns",
        "add_index",
        "expand_keys",
        "width",
        "wrap",
        "format",
        "sort_columns",
        "sort_mode",
    }
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

    meta__config__view_width = MetaSetting(
        help="Default view width mode: min, auto, or terminal",
    )
    meta__view_width = None

    meta__config__view_wrap = MetaSetting(
        help="Default table wrap mode: last or all",
    )
    meta__view_wrap = None

    width = Argument(
        "--width",
        choices=sorted(WIDTH_MODES),
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_WIDTH_HELP,
    )
    wrap = Argument(
        "--wrap",
        choices=sorted(WRAP_MODES),
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help=_WRAP_HELP,
    )

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
        assert isinstance(arguments, dict), f"Got {type(arguments)} instead of dict"

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

    def _apply_meta_view_defaults(self, settings: dict) -> None:
        """Fill unset settings from Meta.view_* defaults."""
        meta_defaults = (
            ("columns", "view_columns", normalize_columns),
            ("sort_columns", "view_sort_columns", normalize_sort_columns),
            ("sort_mode", "view_sort_mode", None),
            ("width", "view_width", None),
            ("wrap", "view_wrap", None),
        )
        for key, meta_name, normalizer in meta_defaults:
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
        self._apply_meta_view_defaults(settings)
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


class ShowViewMixin(_ViewMixinBase):
    """Auto-render command results with :class:`~clak.views.ShowView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--format``, ``--sort-columns``, ``--sort-mode``, ``--width``,
    and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = frozenset(
        {
            "columns",
            "add_index",
            "format",
            "sort_columns",
            "sort_mode",
            "width",
            "wrap",
        }
    )
    meta__cli_view = ShowView

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
        help="Include key/index column in the show table",
    )
    format = Argument(
        "--format",
        choices=["view", "yaml", "json", "csv"],
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help="Output format (default: view table)",
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
        help="Sort direction (default: asc)",
    )


class ListViewMixin(_ViewMixinBase):
    """Auto-render command results with :class:`~clak.views.ListView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--expand-keys`` / ``--no-expand-keys``, ``--format``,
    ``--sort-columns``, ``--sort-mode``, ``--width``, and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = frozenset(
        {
            "columns",
            "add_index",
            "expand_keys",
            "format",
            "sort_columns",
            "sort_mode",
            "width",
            "wrap",
        }
    )
    meta__cli_view = ListView

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
        help="Include index column in the list table",
    )
    expand_keys = Argument(
        "--expand-keys",
        action=argparse.BooleanOptionalAction,
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help="Expand nested dict items into table columns",
    )
    format = Argument(
        "--format",
        choices=["view", "yaml", "json", "csv"],
        default=None,
        group=_OUTPUT_OPTIONS_GROUP,
        help="Output format (default: view table)",
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
        help="Sort direction (default: asc)",
    )


class PprintViewMixin(_ViewMixinBase):
    """Auto-render command results with :class:`~clak.views.PprintView`.

    Adds ``--width``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = frozenset({"width"})
    meta__cli_view = PprintView
