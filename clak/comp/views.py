"""View mixins for automatic CLI rendering and view options.

Mix in one of:
- ShowViewMixin  → ShowView + --columns / --add-index / --format / --sort-columns
- ListViewMixin  → ListView + --columns / --add-index / --expand-keys / --format / --sort-columns
- PprintViewMixin → PprintView + --width

Example:

    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = True  # or False, or ("columns", "add_index")
            view_columns = ("name", "role")
            view_column_names = ("name", "role", "city")
            view_sort_columns = 1

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
                arg.kwargs["help"] = self._column_flag_help(
                    arg.kwargs.get("help", "")
                )
            self.add_argument(key, arg)

    @staticmethod
    def _args_get(args: Any, key: str, default=None):
        if isinstance(args, Mapping):
            return args.get(key, default)
        return getattr(args, key, default)

    # pylint: disable-next=too-many-branches
    def collect_view_settings(self, args: Any) -> dict:
        """Build view render kwargs from parsed CLI args (only set flags)."""
        enabled = self._enabled_view_options()
        settings: dict = {}

        if "columns" in enabled:
            raw = self._args_get(args, "columns", None)
            if raw is not None:
                settings["columns"] = parse_columns(raw)

        if "add_index" in enabled:
            value = self._args_get(args, "add_index", None)
            if value is not None:
                settings["add_index"] = value

        if "expand_keys" in enabled:
            value = self._args_get(args, "expand_keys", None)
            if value is not None:
                settings["expand_keys"] = value

        if "width" in enabled:
            value = self._args_get(args, "width", None)
            if value is not None:
                settings["width"] = value

        if "format" in enabled:
            value = self._args_get(args, "format", None)
            if value is not None:
                settings["format"] = value

        if "sort_columns" in enabled:
            raw = self._args_get(args, "sort_columns", None)
            if raw is not None:
                settings["sort_columns"] = parse_sort_columns(raw)

        if "sort_mode" in enabled:
            value = self._args_get(args, "sort_mode", None)
            if value is not None:
                settings["sort_mode"] = value

        if "columns" not in settings:
            meta_columns = self.query_cfg_parents(
                "view_columns", default=None, include_self=True
            )
            if meta_columns is not None:
                settings["columns"] = normalize_columns(meta_columns)

        if "sort_columns" not in settings:
            meta_sort = self.query_cfg_parents(
                "view_sort_columns", default=None, include_self=True
            )
            if meta_sort is not None:
                settings["sort_columns"] = normalize_sort_columns(meta_sort)

        if "sort_mode" not in settings:
            meta_mode = self.query_cfg_parents(
                "view_sort_mode", default=None, include_self=True
            )
            if meta_mode is not None:
                settings["sort_mode"] = meta_mode

        return settings

    def cli_hook__views(self, instance, ctx, **_):  # pylint: disable=unused-argument
        "Collect view CLI options into ctx.plugins and stash on root for dispatch."
        settings = self.collect_view_settings(ctx.args)
        ctx.plugins["view_settings"] = settings
        setattr(ctx.cli_root, "_clak_view_settings", settings)
        logger.debug("View settings for %s: %s", instance, settings)


class ShowViewMixin(_ViewMixinBase):
    """Auto-render command results with :class:`~clak.views.ShowView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--format``, ``--sort-columns``, and ``--sort-mode``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_cli_option_names = frozenset(
        {"columns", "add_index", "format", "sort_columns", "sort_mode"}
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
    ``--sort-columns``, and ``--sort-mode``.
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

    width = Argument(
        "--width",
        type=int,
        default=None,
        help="Maximum width for pretty-printed output",
    )
