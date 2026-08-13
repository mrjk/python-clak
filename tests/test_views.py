"""Tests for public CLI views, mixins, and parser integration."""

import json
import logging
import re

import pytest

from clak.comp.views import (
    ListViewMixin,
    MarkdownViewMixin,
    PprintViewMixin,
    RawViewMixin,
    RstViewMixin,
    ShowViewMixin,
)
from clak.exception import ClakUserError
from clak.parser import Argument, Command, Parser, ParserNode
from clak.views import (
    ListView,
    MarkdownView,
    PprintView,
    RawView,
    RstView,
    ShowView,
    merge_view_settings,
    normalize_wrap,
    normalize_wrap_min,
    parse_columns,
    parse_sort_columns,
    parse_wrap,
    resolve_view_width,
)

pytestmark = pytest.mark.tags("unit-tests")

USERS = [
    {"name": "ada", "role": "admin", "city": "London"},
    {"name": "linus", "role": "dev", "city": "Helsinki"},
]

USERS_UNSORTED = [
    {"name": "linus", "role": "dev", "city": "Helsinki"},
    {"name": "ada", "role": "admin", "city": "London"},
    {"name": "grace", "role": "dev", "city": "New York"},
]


def _option_flags(app):
    return {opt for action in app.parser._actions for opt in action.option_strings}


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------


def test_parse_columns_comma_separated_and_ints():
    assert parse_columns("name,age") == ["name", "age"]
    assert parse_columns("1, 3") == [1, 3]
    assert parse_columns("-1,2") == [-1, 2]
    assert parse_columns("name,,role") == ["name", "role"]
    assert parse_columns(None) is None


def test_parse_columns_rejects_non_string():
    with pytest.raises(TypeError, match="columns must be a string"):
        parse_columns(["name", "age"])


def test_parse_sort_columns_alias():
    assert parse_sort_columns("name,role") == ["name", "role"]
    assert parse_sort_columns("-1,-3,1") == [-1, -3, 1]
    assert parse_sort_columns(["city", -1]) == ["city", -1]


def test_parse_wrap_keywords_and_columns():
    assert parse_wrap("last") == "last"
    assert parse_wrap("ALL") == "all"
    assert parse_wrap("First") == "first"
    assert parse_wrap("Path,Src") == ["Path", "Src"]
    assert parse_wrap("-1,Src") == [-1, "Src"]
    assert parse_wrap(["Path", "Src", "Path"]) == ["Path", "Src"]
    assert parse_wrap(None) is None


def test_normalize_wrap_and_wrap_min():
    assert normalize_wrap("last") == "last"
    assert normalize_wrap(("Path", "Src")) == ["Path", "Src"]
    assert normalize_wrap(-1) == [-1]
    assert normalize_wrap_min(12) == 12
    assert normalize_wrap_min({"Path": 24, "Src": 12}) == {"Path": 24, "Src": 12}
    with pytest.raises(ValueError, match="wrap_min must be > 0"):
        normalize_wrap_min(0)
    with pytest.raises(TypeError, match="wrap_min must be"):
        normalize_wrap_min("24")


def test_normalize_sort_columns_accepts_sequence():
    from clak.views import normalize_sort_columns

    assert normalize_sort_columns(["name", -1]) == ["name", -1]
    assert normalize_sort_columns("role,-1") == ["role", -1]
    assert normalize_sort_columns(1) == [1]


def test_normalize_columns_accepts_sequence():
    from clak.views import normalize_columns

    assert normalize_columns(["name", "role"]) == ["name", "role"]
    assert normalize_columns("name,role") == ["name", "role"]
    assert normalize_columns(1) == [1]
    assert normalize_columns(None) is None


def test_merge_view_settings_warns_on_override(caplog):
    with caplog.at_level(logging.WARNING):
        merged = merge_view_settings(
            {"columns": ["name"]},
            {"columns": ["age"], "add_index": True},
        )

    assert merged == {"columns": ["age"], "add_index": True}
    assert "overrides view setting" in caplog.text


def test_merge_view_settings_no_warning_when_unset(caplog):
    with caplog.at_level(logging.WARNING):
        merged = merge_view_settings({}, {"columns": ["name"]})

    assert merged == {"columns": ["name"]}
    assert "overrides view setting" not in caplog.text


def test_resolve_view_width_modes():
    assert resolve_view_width(width="content", term_width=80, stdout_tty=True) == (
        "content",
        None,
    )
    assert resolve_view_width(width="fit", term_width=80, stdout_tty=True) == (
        "fit",
        80,
    )
    assert resolve_view_width(width="terminal", term_width=80, stdout_tty=True) == (
        "terminal",
        80,
    )
    assert resolve_view_width(width="terminal", term_width=80, stdout_tty=False) == (
        "content",
        None,
    )
    assert resolve_view_width(width="fit", term_width=None, stdout_tty=True) == (
        "content",
        None,
    )
    # Legacy aliases
    assert resolve_view_width(width="min", term_width=80, stdout_tty=True) == (
        "content",
        None,
    )
    assert resolve_view_width(width="auto", term_width=80, stdout_tty=True) == (
        "fit",
        80,
    )


# ---------------------------------------------------------------------------
# Core views (no mixin)
# ---------------------------------------------------------------------------


def test_show_view_prints_and_returns_rendered_text(capsys):
    rendered = ShowView({"name": "World"}).render()

    assert "World" in rendered
    assert rendered in capsys.readouterr().out


def test_list_view_forwards_options_for_heterogeneous_rows():
    rendered = ListView(
        [{"name": "World"}, {"age": 42}],
        columns=["name", "age"],
        add_index=True,
    ).render(stdout=False)

    assert "Index" in rendered
    assert "World" in rendered
    assert "42" in rendered
    assert "-" in rendered


def test_pprint_view_can_render_without_stdout(capsys):
    rendered = PprintView({"name": "World"}).render(stdout=False)

    assert "World" in rendered
    assert capsys.readouterr().out == ""


def test_dispatch_renders_returned_view(capsys):
    parser = ParserNode()
    parser.cli_run = lambda **_: ShowView({"name": "World"})

    result = parser.dispatch([])

    assert isinstance(result, ShowView)
    assert "World" in capsys.readouterr().out


def test_dispatch_supports_configured_view_class(capsys):
    parser = ParserNode()
    parser.meta__cli_view = ShowView
    parser.cli_run = lambda **_: {"name": "World"}

    result = parser.dispatch([])

    assert result == {"name": "World"}
    assert "World" in capsys.readouterr().out


def test_no_mixin_raw_return_is_silent(capsys):
    class App(Parser):
        def cli_run(self, **_):
            return {"name": "World"}

    result = App(parse=False, add_help=False).dispatch([])

    assert result == {"name": "World"}
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Mixins — auto-render
# ---------------------------------------------------------------------------


def test_list_view_mixin_auto_renders_raw_return(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch([])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" in out
    assert "London" in out


def test_show_view_mixin_auto_renders(capsys):
    class App(ShowViewMixin, Parser):
        def cli_run(self, **_):
            return USERS[0]

    App(parse=False, add_help=False).dispatch([])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "Key" in out


def test_pprint_view_mixin_auto_renders(capsys):
    class App(PprintViewMixin, Parser):
        def cli_run(self, **_):
            return {"name": "ada", "nested": {"a": 1}}

    App(parse=False, add_help=False).dispatch(["--line-length", "nowrap"])

    assert "ada" in capsys.readouterr().out


def test_list_view_mixin_width_cli_option():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    assert "--width" in _option_flags(app)
    app.dispatch(["--width", "fit"])
    settings = getattr(app, "_clak_view_settings", {})
    assert settings.get("width") == "fit"
    assert "term_width" in settings
    assert "stdout_tty" in settings


def test_list_view_mixin_meta_view_width():
    class App(ListViewMixin, Parser):
        class Meta:
            view_width = "min"  # alias for content

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    assert getattr(app, "_clak_view_settings", {}).get("width") == "content"


def test_list_view_mixin_wrap_cli_option():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    assert "--wrap" in _option_flags(app)
    app.dispatch(["--wrap", "all"])
    assert getattr(app, "_clak_view_settings", {}).get("wrap") == "all"


def test_list_view_mixin_meta_view_wrap():
    class App(ListViewMixin, Parser):
        class Meta:
            view_wrap = "all"

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    assert getattr(app, "_clak_view_settings", {}).get("wrap") == "all"


def test_list_view_mixin_wrap_cli_column_list():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch(["--wrap", "name,role"])
    assert getattr(app, "_clak_view_settings", {}).get("wrap") == ["name", "role"]


def test_list_view_mixin_meta_view_wrap_columns_and_min():
    class App(ListViewMixin, Parser):
        class Meta:
            view_wrap = ("name", "city")
            view_wrap_min = {"name": 8}

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    settings = getattr(app, "_clak_view_settings", {})
    assert settings.get("wrap") == ["name", "city"]
    assert settings.get("wrap_min") == {"name": 8}


def test_list_view_mixin_no_wrap_min_flag():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    assert "--wrap-min" not in _option_flags(app)


def test_pprint_view_mixin_has_no_wrap_flag():
    class App(PprintViewMixin, Parser):
        def cli_run(self, **_):
            return {"name": "ada"}

    app = App(parse=False, add_help=False)
    assert "--wrap" not in _option_flags(app)


def test_view_cli_options_false_still_auto_renders(capsys):
    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = False

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    assert "--columns" not in _option_flags(app)

    app.dispatch([])
    assert "ada" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Mixins — CLI options
# ---------------------------------------------------------------------------


def test_list_view_mixin_columns_cli_option(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(["--columns", "name,role"])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" in out
    assert "London" not in out


def test_list_view_mixin_add_index_and_expand_keys(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(["--add-index", "--columns", "name"])

    out = capsys.readouterr().out
    assert "Index" in out
    assert "ada" in out
    assert "admin" not in out


def test_show_view_mixin_columns_and_no_index(capsys):
    class App(ShowViewMixin, Parser):
        def cli_run(self, **_):
            return USERS[0]

    App(parse=False, add_help=False).dispatch(
        ["--columns", "name,role", "--no-add-index"]
    )

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" in out
    assert "London" not in out
    assert "Key" not in out


def test_list_view_mixin_help_lists_view_flags():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    help_text = App(parse=False, add_help=True).parser.format_help()

    assert "--columns" in help_text
    assert "--add-index" in help_text
    assert "--expand-keys" in help_text
    assert "--format" in help_text
    assert "--sort-columns" in help_text
    assert "--sort-mode" in help_text


def test_list_view_mixin_output_options_group_in_help():
    class App(ListViewMixin, Parser):
        catalog = Argument("--catalog", help="Pick a catalog")

        def cli_run(self, **_):
            return USERS

    help_text = App(parse=False, add_help=True).parser.format_help()

    assert "Output options:" in help_text
    assert "--catalog" in help_text
    # View flags sit under the Output options section
    output_idx = help_text.index("Output options:")
    assert help_text.index("--columns", output_idx) > output_idx
    assert help_text.index("--sort-columns", output_idx) > output_idx


def test_list_view_mixin_view_column_names_in_help():
    class App(ListViewMixin, Parser):
        class Meta:
            view_column_names = ("Var", "Value", "Order")

        def cli_run(self, **_):
            return USERS

    help_text = App(parse=False, add_help=True).parser.format_help()

    assert "Available: Var, Value, Order" in help_text
    # --columns, --sort-columns, and --wrap get the Available: suffix
    assert help_text.count("Available: Var, Value, Order") == 3


def test_list_view_mixin_no_available_when_column_names_unset():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "Available:" not in help_text


def test_list_view_mixin_columns_one_based_index(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(["--columns", "1"])

    out = capsys.readouterr().out
    assert "name" in out
    assert "ada" in out
    assert "linus" in out
    assert "admin" not in out
    assert "London" not in out


def test_list_view_mixin_columns_rejects_zero_index(caplog):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(SystemExit) as exc:
            App(parse=False, add_help=False).dispatch(["--columns", "0"])
    assert exc.value.code == 1
    assert "index 0 is invalid" in caplog.text


# ---------------------------------------------------------------------------
# Mixins — output format (Cliff-style)
# ---------------------------------------------------------------------------


def test_list_view_mixin_format_json(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(
        ["--format", "json", "--columns", "name,role"]
    )

    out = capsys.readouterr().out
    records = json.loads(out)
    assert records == [
        {"name": "ada", "role": "admin"},
        {"name": "linus", "role": "dev"},
    ]


def test_list_view_format_json_keeps_original_values():
    """yaml/json must not reuse table display adapts (missing→'-', tabs)."""
    payload = [
        {"name": "ada\tlovelace", "role": "admin", "tags": ["a", "b"]},
        {"name": "linus", "tags": []},
    ]

    rendered = ListView(
        payload, format="json", columns=["name", "role", "tags"]
    ).render(stdout=False)
    records = json.loads(rendered)

    assert records == [
        {"name": "ada\tlovelace", "role": "admin", "tags": ["a", "b"]},
        {"name": "linus", "tags": []},
    ]
    assert all("-" not in record.values() for record in records)


def test_list_view_mixin_format_csv(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(
        ["--format", "csv", "--columns", "name,role"]
    )

    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert lines[0] == "name,role"
    assert "ada,admin" in lines
    assert "linus,dev" in lines


def test_list_view_mixin_format_yaml(capsys):
    pytest.importorskip("yaml")

    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(["--format", "yaml", "--columns", "name"])

    out = capsys.readouterr().out
    assert "name: ada" in out
    assert "name: linus" in out


def test_show_view_mixin_format_json(capsys):
    class App(ShowViewMixin, Parser):
        def cli_run(self, **_):
            return USERS[0]

    App(parse=False, add_help=False).dispatch(["--format", "json"])

    out = capsys.readouterr().out
    record = json.loads(out)
    assert record["name"] == "ada"
    assert record["role"] == "admin"


def test_list_view_mixin_sort_columns_asc(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(
        ["--sort-columns", "name", "--columns", "name,role"]
    )

    out = capsys.readouterr().out
    assert out.index("ada") < out.index("linus")


def test_list_view_mixin_sort_columns_desc(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(
        [
            "--sort-columns",
            "name",
            "--sort-mode",
            "desc",
            "--columns",
            "name,role",
        ]
    )

    out = capsys.readouterr().out
    assert out.index("linus") < out.index("ada")


def test_list_view_mixin_default_sorts_first_column_asc(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS_UNSORTED

    App(parse=False, add_help=False).dispatch([])

    out = capsys.readouterr().out
    assert out.index("ada") < out.index("grace") < out.index("linus")


def test_list_view_mixin_meta_view_sort_columns(capsys):
    class App(ListViewMixin, Parser):
        class Meta:
            view_sort_columns = ("city",)
            view_sort_mode = "desc"

        def cli_run(self, **_):
            return USERS_UNSORTED

    App(parse=False, add_help=False).dispatch([])

    out = capsys.readouterr().out
    assert out.index("grace") < out.index("ada") < out.index("linus")


def test_list_view_mixin_meta_view_columns(capsys):
    class App(ListViewMixin, Parser):
        class Meta:
            view_columns = ("name", "city")
            view_sort_columns = 1

        def cli_run(self, **_):
            return USERS_UNSORTED

    App(parse=False, add_help=False).dispatch([])

    out = capsys.readouterr().out
    assert "name" in out
    assert "city" in out
    assert "role" not in out.split("\n")[0]
    # sort by column 1 (name): ada, grace, linus
    assert out.index("ada") < out.index("grace") < out.index("linus")


def test_list_view_mixin_columns_cli_overrides_meta(capsys):
    class App(ListViewMixin, Parser):
        class Meta:
            view_columns = ("name", "city")

        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(["--columns", "name,role"])

    out = capsys.readouterr().out
    assert "role" in out
    assert "admin" in out
    assert "London" not in out


def test_list_view_mixin_sort_columns_negative_indexes(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS_UNSORTED

    App(parse=False, add_help=False).dispatch(
        ["--sort-columns", "-1", "--columns", "name,city"]
    )

    out = capsys.readouterr().out
    # -1 = city column; asc -> Helsinki, London, New York
    assert out.index("linus") < out.index("ada") < out.index("grace")


def test_list_view_mixin_sort_columns_mixed_indexes(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS_UNSORTED

    App(parse=False, add_help=False).dispatch(
        ["--sort-columns=-1,-2,1", "--columns", "name,role,city"]
    )

    out = capsys.readouterr().out
    assert "ada" in out
    assert "linus" in out


def test_subcommand_list_view_mixin_format_json(capsys):
    class VarsCmd(ListViewMixin, Parser):
        "List users."

        def cli_run(self, **_):
            return USERS

    class Root(Parser):
        "Root."

        vars = Command(VarsCmd)

    app = Root(parse=False, add_help=False)
    app.dispatch(["vars", "--format", "json", "--columns", "name,role"])

    settings = getattr(app, "_clak_view_settings", {})
    assert settings["format"] == "json"
    assert settings["columns"] == ["name", "role"]
    assert "term_width" in settings
    assert "stdout_tty" in settings
    records = json.loads(capsys.readouterr().out)
    assert len(records) == 2
    assert set(records[0]) == {"name", "role"}


def test_list_view_mixin_sort_applies_to_json(capsys):
    """--sort-columns must reorder --format json output."""

    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS_UNSORTED

    App(parse=False, add_help=False).dispatch(
        ["--format", "json", "--sort-columns", "name", "--columns", "name,role"]
    )
    records = json.loads(capsys.readouterr().out)
    assert [row["name"] for row in records] == ["ada", "grace", "linus"]


def test_list_view_mixin_meta_view_format_and_add_index(capsys):
    class App(ListViewMixin, Parser):
        class Meta:
            view_format = "json"
            view_columns = ("name",)
            view_add_index = False
            view_expand_keys = True

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    settings = getattr(app, "_clak_view_settings", {})
    assert settings["format"] == "json"
    assert settings["columns"] == ["name"]
    assert settings["add_index"] is False
    assert settings["expand_keys"] is True
    records = json.loads(capsys.readouterr().out)
    assert all(set(row) == {"name"} for row in records)


def test_show_view_mixin_exposes_table_options_not_expand_keys():
    class App(ShowViewMixin, Parser):
        def cli_run(self, **_):
            return USERS[0]

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--columns" in flags
    assert "--format" in flags
    assert "--width" in flags
    assert "--wrap" in flags
    assert "--expand-keys" not in flags


def test_pprint_view_mixin_exposes_only_line_length():
    class App(PprintViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--line-length" in flags
    assert "--width" not in flags
    assert "--columns" not in flags
    assert "--format" not in flags
    assert "--wrap" not in flags
    assert "--expand-keys" not in flags


# ---------------------------------------------------------------------------
# Mixins — nested subcommand (hooks must fire on child nodes)
# ---------------------------------------------------------------------------


def test_subcommand_list_view_mixin_columns(capsys):
    class VarsCmd(ListViewMixin, Parser):
        "List users."

        def cli_run(self, **_):
            return USERS

    class Root(Parser):
        "Root."

        vars = Command(VarsCmd)

    app = Root(parse=False, add_help=False)
    app.dispatch(["vars", "--columns", "name,role"])

    settings = getattr(app, "_clak_view_settings", {})
    assert settings["columns"] == ["name", "role"]
    assert "term_width" in settings
    assert "stdout_tty" in settings
    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" in out
    assert "London" not in out


def test_subcommand_list_view_mixin_add_index(capsys):
    class VarsCmd(ListViewMixin, Parser):
        "List users."

        def cli_run(self, **_):
            return USERS

    class Root(Parser):
        "Root."

        vars = Command(VarsCmd)

    Root(parse=False, add_help=False).dispatch(
        ["vars", "--add-index", "--columns", "name"]
    )

    out = capsys.readouterr().out
    assert "Index" in out
    assert "ada" in out
    assert "admin" not in out


# ---------------------------------------------------------------------------
# Mixins — Meta.view_cli_options
# ---------------------------------------------------------------------------


def test_view_cli_options_false_hides_flags():
    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = False

        def cli_run(self, **_):
            return USERS

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--columns" not in flags
    assert "--add-index" not in flags
    assert "--expand-keys" not in flags


def test_view_cli_options_subset():
    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = ("columns",)

        def cli_run(self, **_):
            return USERS

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--columns" in flags
    assert "--add-index" not in flags
    assert "--expand-keys" not in flags


def test_view_cli_options_unknown_name_raises():
    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = ("columns", "nope")

        def cli_run(self, **_):
            return USERS

    with pytest.raises(ValueError, match="Unknown view_cli_options"):
        App(parse=False, add_help=False)


def test_view_cli_options_invalid_type_raises():
    class App(ListViewMixin, Parser):
        class Meta:
            view_cli_options = "columns"

        def cli_run(self, **_):
            return USERS

    with pytest.raises(TypeError, match="view_cli_options must be"):
        App(parse=False, add_help=False)


# ---------------------------------------------------------------------------
# Mixins — explicit view + CLI override
# ---------------------------------------------------------------------------


def test_explicit_view_still_works_with_mixin_and_cli_override(capsys, caplog):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return ListView(USERS, columns=["name", "role"])

    with caplog.at_level(logging.WARNING):
        App(parse=False, add_help=False).dispatch(["--columns", "name"])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" not in out
    assert "overrides view setting" in caplog.text


def test_example_script_exceptions_runs(capsys):
    """Smoke-test the documented exception-handling example."""
    import importlib.util
    import sys
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "examples" / "script_exceptions.py"
    spec = importlib.util.spec_from_file_location("script_exceptions_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with pytest.raises(SystemExit) as exc:
        module.AppMain(parse=False, add_help=False).dispatch(["deploy", "missing"])
    assert exc.value.code == 44
    assert "not found" in capsys.readouterr().err


def test_example_script_views_runs(capsys):
    """Smoke-test the documented example module."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "examples" / "script_views.py"
    spec = importlib.util.spec_from_file_location("script_views_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.AppMain(parse=False, add_help=False).dispatch(["--columns", "name,role"])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" in out
    assert "London" not in out


# ---------------------------------------------------------------------------
# Text views — Raw / Markdown / Rst
# ---------------------------------------------------------------------------


MD_SAMPLE = "# Hello\n\n**bold** and `code`"
MD_FENCE_SAMPLE = """# Title

Use `inline` here.

```yaml
title: Traefik Web
description: Reverse proxy
```

```json
{"title": "Traefik Web"}
```
"""
RST_SAMPLE = "Hello\n=====\n\nThis is **strong** text.\n"


def test_raw_view_mixin_prints_text(capsys):
    class App(RawViewMixin, Parser):
        def cli_run(self, **_):
            return "plain text line"

    App(parse=False, add_help=False).dispatch([])
    assert capsys.readouterr().out.strip() == "plain text line"


def test_raw_view_mixin_exposes_only_line_length():
    class App(RawViewMixin, Parser):
        def cli_run(self, **_):
            return "x"

    flags = _option_flags(App(parse=False, add_help=False))
    assert "--line-length" in flags
    assert "--width" not in flags
    assert "--format" not in flags
    assert "--wrap" not in flags
    assert "--columns" not in flags


def test_markdown_view_mixin_format_raw_without_rich(capsys):
    class App(MarkdownViewMixin, Parser):
        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch(["--format", "raw"])
    out = capsys.readouterr().out
    assert "# Hello" in out
    assert "**bold**" in out


def test_rst_view_mixin_format_raw_without_docutils(capsys):
    class App(RstViewMixin, Parser):
        def cli_run(self, **_):
            return RST_SAMPLE

    App(parse=False, add_help=False).dispatch(["--format", "raw"])
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "=====" in out
    assert "**strong**" in out


def test_markdown_view_mixin_format_choices_are_text_only():
    class App(MarkdownViewMixin, Parser):
        def cli_run(self, **_):
            return MD_SAMPLE

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "--format" in help_text
    assert "raw" in help_text
    assert "yaml" not in help_text
    assert "csv" not in help_text
    assert "--wrap" not in help_text


def test_list_view_mixin_format_choices_remain_table():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "{view,yaml,json,csv}" in help_text or (
        "yaml" in help_text and "json" in help_text and "csv" in help_text
    )
    assert "raw" not in help_text.split("--format")[1].split("\n")[0]


def test_markdown_view_renders_with_rich(capsys):
    pytest.importorskip("rich")

    class App(MarkdownViewMixin, Parser):
        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "# Hello" not in out


def _has_background_csi(text: str) -> bool:
    """True if *text* sets a token/pane background (not default-bg or underline)."""
    if "\x1b[48;" in text:
        return True
    for seq in re.findall(r"\x1b\[([0-9;]*)m", text):
        if not seq:
            continue
        for code in seq.split(";"):
            if not code:
                continue
            number = int(code)
            if 40 <= number <= 47 or number == 48 or 100 <= number <= 107:
                return True
    return False


def test_markdown_view_code_is_fg_only():
    pytest.importorskip("rich")
    rendered = MarkdownView(MD_FENCE_SAMPLE).render(stdout=False)
    assert "Traefik Web" in rendered
    assert "inline" in rendered
    assert "\x1b[" in rendered
    assert not _has_background_csi(rendered)


def test_markdown_view_monokai_theme_has_no_background_csi():
    pytest.importorskip("rich")
    rendered = MarkdownView(MD_FENCE_SAMPLE, theme="monokai").render(stdout=False)
    assert "\x1b[" in rendered
    assert not _has_background_csi(rendered)


def test_markdown_view_mixin_meta_syntax_theme(monkeypatch, capsys):
    pytest.importorskip("rich")
    from clak.views.rich_style import CLAK_SYNTAX_THEME_ENV, resolve_syntax_theme

    monkeypatch.setenv(CLAK_SYNTAX_THEME_ENV, "vim")
    seen = {}
    real = resolve_syntax_theme

    def _spy(theme=None):
        result = real(theme)
        seen["arg"] = theme
        seen["result"] = result
        return result

    monkeypatch.setattr("clak.views.rich_style.resolve_syntax_theme", _spy)
    monkeypatch.setattr("clak.views.text.resolve_syntax_theme", _spy)

    class App(MarkdownViewMixin, Parser):
        class Meta:
            view_syntax_theme = "monokai"

        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    capsys.readouterr()
    assert seen["arg"] == "monokai"
    assert seen["result"] == "monokai"


def test_rst_view_renders_with_docutils(capsys):
    pytest.importorskip("docutils")

    class App(RstViewMixin, Parser):
        def cli_run(self, **_):
            return RST_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "strong" in out
    assert "=====" not in out


def test_markdown_view_missing_rich_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(ClakUserError) as exc:
        MarkdownView("# hi").render(stdout=False)
    # Undo block before assertions so pytest-clarity can import rich for diffs
    monkeypatch.undo()
    assert "rich" in str(exc.value.message).lower()
    assert "mrjk.clak[markdown]" in (exc.value.advice or "")


def test_rst_view_missing_docutils_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "docutils" or name.startswith("docutils."):
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(ClakUserError) as exc:
        RstView("Title\n=====\n").render(stdout=False)
    monkeypatch.undo()
    assert "docutils" in str(exc.value.message).lower()
    assert "mrjk.clak[rst]" in (exc.value.advice or "")


def test_markdown_view_meta_view_format_raw(capsys):
    class App(MarkdownViewMixin, Parser):
        class Meta:
            view_format = "raw"

        def cli_run(self, **_):
            return MD_SAMPLE

    App(parse=False, add_help=False).dispatch([])
    out = capsys.readouterr().out
    assert "**bold**" in out


def test_as_text_coerces_non_string():
    assert RawView(42).render(stdout=False) == "42"
    assert RawView(None).render(stdout=False) == ""


# ---------------------------------------------------------------------------
# CompositeView
# ---------------------------------------------------------------------------


def test_composite_view_order_and_blank_separators():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada"}])),
            ("notes", RawView("hello notes")),
            ("more", ListView([{"name": "linus"}])),
        ],
        width="min",
    ).render(stdout=False)

    assert "ada" in out
    assert "hello notes" in out
    assert "linus" in out
    assert "\n\nhello notes\n\n" in out


def test_composite_view_shared_table_width_min():
    from clak.views import CompositeView

    primary = ListView(
        [{"name": "a", "role": "admin", "city": "London"}],
    )
    secondary = ListView([{"n": "x"}])
    out = CompositeView(
        [("primary", primary), ("secondary", secondary)],
        width="min",
    ).render(stdout=False)

    blocks = [b for b in out.split("\n\n") if b.strip()]
    assert len(blocks) == 2
    widths = [len(block.splitlines()[0]) for block in blocks]
    assert widths[0] == widths[1]


def test_composite_format_scope_first_json_matches_primary():
    from clak.views import CompositeView

    rows = [{"name": "ada", "role": "admin"}]
    primary_only = ListView(rows).render(stdout=False, format="json")
    composite = CompositeView(
        [
            ("users", ListView(rows)),
            ("notes", RawView("skip me")),
        ],
        format="json",
        format_scope="first",
    ).render(stdout=False)
    assert json.loads(composite) == json.loads(primary_only)


def test_composite_format_scope_all_envelope_json():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada"}])),
            ("notes", RawView("## Notes")),
        ],
        format="json",
        format_scope="all",
    ).render(stdout=False)
    payload = json.loads(out)
    assert payload == {
        "sections": [
            {"name": "users", "kind": "list", "data": [{"name": "ada"}]},
            {"name": "notes", "kind": "raw", "data": "## Notes"},
        ]
    }


def test_composite_format_scope_all_csv_blocks():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada"}])),
            ("notes", RawView("plain")),
        ],
        format="csv",
        format_scope="all",
    ).render(stdout=False)
    assert "# section: users" in out
    assert "# section: notes" in out
    assert "ada" in out
    assert "plain" in out


def test_composite_primary_override_and_columns():
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("users", ListView([{"name": "ada", "role": "admin"}])),
            ("related", ListView([{"id": 1, "label": "x"}])),
        ],
        primary="related",
        format="json",
        format_scope="first",
        columns=["label"],
    ).render(stdout=False)
    assert json.loads(out) == [{"label": "x"}]


def test_composite_show_view_primary_with_markdown():
    pytest.importorskip("rich")
    from clak.views import CompositeView

    out = CompositeView(
        [
            ("summary", ShowView({"App": "demo:web", "Name": "Demo"})),
            ("docs", MarkdownView("# Demo README\n\nLong body.")),
        ],
        width="min",
    ).render(stdout=False)
    assert "demo:web" in out
    assert "Long body." in out
    assert "=== Docs ===" not in out


def test_composite_section_title_and_description():
    from clak.views import CompositeView

    out = CompositeView(
        [
            (
                "users",
                ListView([{"name": "ada"}]),
                {
                    "title": "Users",
                    "description": "People with access.",
                },
            ),
            ("notes", RawView("hello notes"), {"title": "Notes"}),
        ],
        width="min",
    ).render(stdout=False)
    assert out.startswith("=== Users ===\nPeople with access.\n\n")
    assert "=== Notes ===\n\nhello notes" in out


def test_composite_section_meta_in_envelope_json():
    from clak.views import CompositeView

    out = CompositeView(
        [
            (
                "users",
                ListView([{"name": "ada"}]),
                {"title": "Users", "description": "People with access."},
            ),
            ("notes", RawView("skip")),
        ],
        format="json",
        format_scope="all",
    ).render(stdout=False)
    payload = json.loads(out)
    assert payload["sections"][0]["title"] == "Users"
    assert payload["sections"][0]["description"] == "People with access."
    assert "title" not in payload["sections"][1]


def test_composite_view_mixin_format_scope_cli(capsys):
    from clak import CompositeViewMixin
    from clak.views import CompositeView

    class App(CompositeViewMixin, Parser):
        def cli_run(self, **_):
            return CompositeView(
                [
                    ("users", ListView([{"name": "ada", "role": "admin"}])),
                    ("notes", RawView("extra")),
                ]
            )

    App(parse=False, add_help=False).dispatch(
        ["--format", "json", "--format-scope", "all"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["sections"]) == 2
    assert payload["sections"][1]["data"] == "extra"


def test_composite_view_mixin_meta_format_scope(capsys):
    from clak import CompositeViewMixin
    from clak.views import CompositeView

    class App(CompositeViewMixin, Parser):
        class Meta:
            view_format_scope = "all"
            view_format = "json"

        def cli_run(self, **_):
            return CompositeView(
                [
                    ("users", ListView([{"name": "ada"}])),
                    ("notes", RawView("meta")),
                ]
            )

    App(parse=False, add_help=False).dispatch([])
    payload = json.loads(capsys.readouterr().out)
    assert payload["sections"][1]["data"] == "meta"


def test_composite_view_mixin_exposes_format_scope_flag():
    from clak import CompositeViewMixin

    class App(CompositeViewMixin, Parser):
        def cli_run(self, **_):
            return None

    assert "--format-scope" in _option_flags(App(parse=False, add_help=False))


def test_composite_unknown_primary_raises():
    from clak.views import CompositeView

    with pytest.raises(ValueError, match="primary section"):
        CompositeView(
            [("users", ListView([{"name": "ada"}]))],
            primary="missing",
        ).render(stdout=False)
