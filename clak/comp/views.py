"""View mixins for automatic CLI rendering and view options.

Every view option is declared once as a :class:`ViewOption` (flag, help,
CLI parser, ``Meta.view_<name>`` normalizer). A mixin lists the options it
adds in ``_view_options``; the ``--flag`` Argument and the
``meta__config__view_<name>`` declaration are generated from it, and
settings collection iterates the same registry.

Option layers (mirror ClakView hierarchy):

1. ClakViewOptMixin — generic (no CLI flags)
2. TableViewOptMixin — table (Show/List): ``width``, ``columns``,
   ``add_index``, ``format``, ``sort_columns``, ``sort_mode``, ``wrap``,
   ``yaml_cells``
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
            view_width = "fit"
            view_wrap = "last"

        def cli_run(self, **_):
            return [{"name": "a"}, {"name": "b"}]
"""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Set, Tuple

from clak.core.descriptors import Argument, MetaSetting
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
)
from clak.views.base import normalize_width_mode, parse_line_length
from clak.views.table import (
    normalize_columns,
    normalize_sort_columns,
    normalize_wrap,
    normalize_wrap_min,
    parse_columns,
    parse_sort_columns,
    parse_wrap,
)

logger = logging.getLogger(__name__)

_OUTPUT_OPTIONS_GROUP = "Output options"
_BOOL_FLAG = {"action": argparse.BooleanOptionalAction}


@dataclass(frozen=True)
class ViewOption:
    """One view option: CLI flag, ``Meta.view_<name>`` default, and parsers.

    Attributes:
        name: Settings key and argparse dest (``columns``).
        help: ``--flag`` help text.
        meta_help: Help for ``meta__config__view_<name>``.
        arg_kwargs: Extra ``Argument`` kwargs (choices, action, metavar...).
        parse: CLI string -> setting (None: use the parsed value as-is).
        normalize: ``Meta`` value -> setting (None: use as-is).
    """

    name: str
    help: str
    meta_help: str
    arg_kwargs: Mapping[str, Any] = field(default_factory=dict)
    parse: Optional[Callable[[Any], Any]] = None
    normalize: Optional[Callable[[Any], Any]] = None

    @property
    def flag(self) -> str:
        """``--kebab-case`` flag for this option."""
        return "--" + self.name.replace("_", "-")

    @property
    def meta_name(self) -> str:
        """``Meta`` attribute holding the default (``view_<name>``)."""
        return f"view_{self.name}"

    def argument(self) -> Argument:
        """Build the CLI ``Argument`` (default None = unset)."""
        return Argument(
            self.flag,
            default=None,
            option_group=_OUTPUT_OPTIONS_GROUP,
            help=self.help,
            **self.arg_kwargs,
        )


_COLUMN_SPEC = "(string, int index, or sequence; same syntax as --{flag})"

WIDTH = ViewOption(
    "width",
    help=(
        "Table width: content (size to data), fit (shrink if wider than "
        "terminal), terminal (use terminal width). No wrap when stdout "
        "is not a TTY."
    ),
    meta_help="Default table width: content, fit, or terminal",
    arg_kwargs={"choices": sorted(WIDTH_MODES)},
    normalize=normalize_width_mode,
)
COLUMNS = ViewOption(
    "columns",
    help=(
        "Comma-separated columns to display (names, 1-based indexes, "
        "or negatives from end: -1=last)"
    ),
    meta_help="Default columns when --columns is unset "
    + _COLUMN_SPEC.format(flag="columns"),
    parse=parse_columns,
    normalize=normalize_columns,
)
ADD_INDEX = ViewOption(
    "add_index",
    help="Include key/index column in the table",
    meta_help="Default for --add-index / --no-add-index",
    arg_kwargs=_BOOL_FLAG,
)
YAML_CELLS = ViewOption(
    "yaml_cells",
    help="Render list/dict cells as YAML in table view (default: on)",
    meta_help="Default for --yaml-cells / --no-yaml-cells",
    arg_kwargs=_BOOL_FLAG,
)
TABLE_FORMAT = ViewOption(
    "format",
    help="Output format (default: view table)",
    meta_help="Default output format: view, yaml, json, or csv",
    arg_kwargs={"choices": ["view", "yaml", "json", "csv"]},
)
SORT_COLUMNS = ViewOption(
    "sort_columns",
    help=(
        "Comma-separated columns to sort by (names, 1-based indexes, "
        "or negatives from end: -1=last). Use --sort-columns=-1,1 when "
        "values start with '-'."
    ),
    meta_help="Default sort columns when --sort-columns is unset "
    + _COLUMN_SPEC.format(flag="sort-columns"),
    parse=parse_sort_columns,
    normalize=normalize_sort_columns,
)
SORT_MODE = ViewOption(
    "sort_mode",
    help="Sort direction (default: asc)",
    meta_help="Default sort mode: asc or desc",
    arg_kwargs={"choices": ["asc", "desc"]},
)
WRAP = ViewOption(
    "wrap",
    help=(
        "Flexible table columns: they expand or shrink to the terminal. "
        "last (rightmost), first (leftmost), all (any column), or "
        "comma-separated names/indexes in priority order. Use --wrap=-1 "
        "when the value starts with '-'. Ignored when width is content or "
        "stdout is not a TTY."
    ),
    meta_help=(
        "Flexible table columns: last, first, all, or column "
        "names/indexes (same syntax as --columns)"
    ),
    arg_kwargs={"metavar": "MODE|COL,..."},
    parse=parse_wrap,
    normalize=normalize_wrap,
)
EXPAND_KEYS = ViewOption(
    "expand_keys",
    help="Expand nested dict items into table columns",
    meta_help="Default for --expand-keys / --no-expand-keys",
    arg_kwargs=_BOOL_FLAG,
)
LINE_LENGTH = ViewOption(
    "line_length",
    help=(
        "Wrap text at N columns (default 120), terminal, or nowrap. "
        "No wrap when stdout is not a TTY."
    ),
    meta_help="Default text wrap: positive int, terminal, or nowrap",
    arg_kwargs={"type": parse_line_length, "metavar": "N|terminal|nowrap"},
    normalize=parse_line_length,
)
TEXT_FORMAT = ViewOption(
    "format",
    help="Output format: view (rendered) or raw (source). Default: view",
    meta_help="Default output format: view (rendered) or raw (source)",
    arg_kwargs={"choices": sorted(TEXT_FORMATS)},
)
DATA_FORMAT = ViewOption(
    "format",
    help=(
        "Output format: json or yaml. Default: yaml when PyYAML is "
        "installed, else json"
    ),
    meta_help="Default data format: json, yaml, or unset for auto",
    arg_kwargs={"choices": sorted(DATA_FORMATS)},
)
COMPACT = ViewOption(
    "compact",
    help="Compact JSON (single line). Ignored for YAML. Default: off",
    meta_help="Default for --compact / --no-compact (JSON only)",
    arg_kwargs=_BOOL_FLAG,
)
COLOR = ViewOption(
    "color",
    help=(
        "Colorize JSON/YAML with rich when available. Default: on for TTY "
        "when CLAK_COLORS is enabled"
    ),
    meta_help="Default for --color / --no-color",
    arg_kwargs=_BOOL_FLAG,
)
ANCHORS = ViewOption(
    "anchors",
    help=(
        "Allow YAML anchors/aliases for shared references. Ignored for "
        "JSON. Default: on"
    ),
    meta_help="Default for --anchors / --no-anchors (YAML only)",
    arg_kwargs=_BOOL_FLAG,
)
FORMAT_SCOPE = ViewOption(
    "format_scope",
    help=(
        "When using CompositeView with machine formats: first (primary "
        "section only) or all (envelope of every section). Default: first"
    ),
    meta_help="Default format scope for CompositeView: first or all",
    arg_kwargs={"choices": sorted(FORMAT_SCOPES)},
)

# Every declared view option (``*_FORMAT`` share the ``format`` dest).
VIEW_OPTIONS = (
    WIDTH,
    COLUMNS,
    ADD_INDEX,
    TABLE_FORMAT,
    SORT_COLUMNS,
    SORT_MODE,
    WRAP,
    YAML_CELLS,
    EXPAND_KEYS,
    LINE_LENGTH,
    TEXT_FORMAT,
    DATA_FORMAT,
    COMPACT,
    COLOR,
    ANCHORS,
    FORMAT_SCOPE,
)
# Every view option dest, across all mixins (used to filter Arguments).
_ALL_VIEW_OPTION_NAMES = frozenset(opt.name for opt in VIEW_OPTIONS)

_SYNTAX_THEME_SETTING = MetaSetting(
    help=(
        "Pygments/Rich Syntax theme for DataView and Markdown code. "
        "Overrides CLAK_SYNTAX_THEME; default ansi_dark"
    ),
)


class _ViewMixinBase:
    """Shared view-mixin plumbing: option registry, hook, settings collection."""

    # Options added by this class (not inherited); see ``_view_option_map``.
    _view_options: Tuple[ViewOption, ...] = ()
    # When True, ``Meta.view_syntax_theme`` feeds the ``theme`` setting.
    _uses_syntax_theme = False

    meta__config__view_cli_options = MetaSetting(
        help=(
            "Which view CLI options to expose: True (all), False (none), "
            "or a sequence of option names"
        ),
    )

    def __init_subclass__(cls, **kwargs):
        """Materialize ``--flag`` Arguments and Meta declarations."""
        super().__init_subclass__(**kwargs)
        for opt in vars(cls).get("_view_options", ()):
            if opt.name not in vars(cls):
                setattr(cls, opt.name, opt.argument())
            setattr(
                cls, f"meta__config__{opt.meta_name}", MetaSetting(help=opt.meta_help)
            )

    @classmethod
    def _view_option_map(cls) -> Dict[str, ViewOption]:
        """Options of this mixin stack, nearest class wins per name."""
        out: Dict[str, ViewOption] = {}
        for klass in reversed(cls.__mro__):
            for opt in vars(klass).get("_view_options", ()):
                out[opt.name] = opt
        return out

    def _enabled_view_options(self, node=None) -> Set[str]:
        """View option names enabled by ``Meta.view_cli_options`` on *node*."""
        node = node or self
        available = set(self._view_option_map())
        configured = node.query_cfg_parents("view_cli_options", default=True)
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
        names = self.query_cfg_parents("view_column_names", default=None)
        if not names:
            return base_help
        available = ", ".join(str(name) for name in names)
        base = base_help.rstrip()
        if base.endswith("."):
            return f"{base} Available: {available}"
        return f"{base}. Available: {available}"

    def _skip_argument_names(self) -> Set[str]:
        return _ALL_VIEW_OPTION_NAMES - self._enabled_view_options()

    def _prepare_argument(self, key: str, arg: Argument) -> Argument:
        arg = super()._prepare_argument(key, arg)
        if key in (COLUMNS.name, SORT_COLUMNS.name, WRAP.name):
            arg = arg.with_kwargs(
                help=self._column_flag_help(arg.kwargs.get("help", ""))
            )
        return arg

    @staticmethod
    def _args_get(args: Any, key: str, default=None):
        if isinstance(args, Mapping):
            return args.get(key, default)
        return getattr(args, key, default)

    def collect_view_settings(self, args: Any, node=None) -> dict:
        """Build view render kwargs: set CLI flags, then ``Meta.view_*``.

        *node* is the parser whose ``Meta`` supplies defaults (default: self).
        """
        node = node or self
        options = self._view_option_map()
        enabled = self._enabled_view_options(node)
        settings: dict = {}
        for name, opt in options.items():
            if name not in enabled:
                continue
            raw = self._args_get(args, name, None)
            if raw is not None:
                settings[name] = opt.parse(raw) if opt.parse else raw
                continue
            value = node.query_cfg_parents(opt.meta_name, default=None)
            if value is not None:
                settings[name] = opt.normalize(value) if opt.normalize else value

        if WRAP.name in options:
            value = node.query_cfg_parents("view_wrap_min", default=None)
            if value is not None:
                settings["wrap_min"] = normalize_wrap_min(value)

        if self._uses_syntax_theme:
            value = node.query_cfg_parents("view_syntax_theme", default=None)
            if value is not None:
                settings["theme"] = value
        return settings

    def cli_hook__views(self, instance, ctx, **_):
        "Collect view CLI options into ctx.plugins['view_settings']."
        settings = self.collect_view_settings(ctx.args, node=instance)
        ctx.plugins["view_settings"] = settings
        logger.debug("View settings for %s: %s", instance, settings)


class ClakViewOptMixin(_ViewMixinBase):
    """Layer 1: generic ClakView (no CLI flags)."""


class TableViewOptMixin(ClakViewOptMixin):
    """Layer 2: table view options shared by Show and List."""

    _view_options = (
        WIDTH,
        COLUMNS,
        ADD_INDEX,
        TABLE_FORMAT,
        SORT_COLUMNS,
        SORT_MODE,
        WRAP,
        YAML_CELLS,
    )

    meta__config__view_column_names = MetaSetting(
        help=(
            "Full set of selectable column names shown in --columns / "
            "--sort-columns help (view_columns remains the default display subset)"
        ),
    )
    meta__config__view_wrap_min = MetaSetting(
        help=(
            "Shrink floor for flexible columns: positive int (all of them) "
            "or mapping of column spec to positive int"
        ),
    )


class ShowViewMixin(TableViewOptMixin):
    """Auto-render command results with :class:`~clak.views.ShowView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--format``, ``--sort-columns``, ``--sort-mode``, ``--width``,
    and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    meta__cli_view = ShowView


class ListViewMixin(TableViewOptMixin):
    """Auto-render command results with :class:`~clak.views.ListView`.

    Adds ``--columns``, ``--add-index`` / ``--no-add-index``,
    ``--expand-keys`` / ``--no-expand-keys``, ``--format``,
    ``--sort-columns``, ``--sort-mode``, ``--width``, and ``--wrap``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_options = (EXPAND_KEYS,)
    meta__cli_view = ListView


class TextLayoutOptMixin(ClakViewOptMixin):
    """Text wrap options shared by Raw, Pprint, Markdown, Rst, and Composite."""

    _view_options = (LINE_LENGTH,)


class PprintViewMixin(TextLayoutOptMixin):
    """Auto-render command results with :class:`~clak.views.PprintView`.

    Adds ``--line-length``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    meta__cli_view = PprintView


class TextViewOptMixin(TextLayoutOptMixin):
    """Layer 2: text view options shared by Markdown and Rst."""

    _view_options = (TEXT_FORMAT,)


class RawViewMixin(TextLayoutOptMixin):
    """Auto-render command results with :class:`~clak.views.RawView`.

    Adds ``--line-length``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    meta__cli_view = RawView


class MarkdownViewMixin(TextViewOptMixin):
    """Auto-render command results with :class:`~clak.views.MarkdownView`.

    Adds ``--format`` (``view`` / ``raw``) and ``--line-length``.
    Syntax theme: ``Meta.view_syntax_theme`` or ``CLAK_SYNTAX_THEME``, else
    ``ansi_dark``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _uses_syntax_theme = True
    meta__cli_view = MarkdownView
    meta__config__view_syntax_theme = _SYNTAX_THEME_SETTING


class RstViewMixin(TextViewOptMixin):
    """Auto-render command results with :class:`~clak.views.RstView`.

    Adds ``--format`` (``view`` / ``raw``) and ``--line-length``.
    Configure exposed flags with ``Meta.view_cli_options``.
    """

    meta__cli_view = RstView


class DataViewMixin(_ViewMixinBase):
    """Auto-render command results with :class:`~clak.views.DataView`.

    Adds ``--format`` (``json`` / ``yaml``), ``--compact`` / ``--no-compact``,
    ``--color`` / ``--no-color``, and ``--anchors`` / ``--no-anchors``.
    Syntax theme: ``Meta.view_syntax_theme`` or ``CLAK_SYNTAX_THEME``, else
    ``ansi_dark``. Configure exposed flags with ``Meta.view_cli_options``.
    """

    _view_options = (DATA_FORMAT, COMPACT, COLOR, ANCHORS)
    _uses_syntax_theme = True
    meta__cli_view = DataView
    meta__config__view_syntax_theme = _SYNTAX_THEME_SETTING


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

    _view_options = (EXPAND_KEYS, FORMAT_SCOPE)
