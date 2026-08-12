"""Tests for public CLI views, mixins, and parser integration."""

import json
import logging

import pytest

from clak.comp.views import ListViewMixin, PprintViewMixin, ShowViewMixin
from clak.parser import Argument, Command, Parser, ParserNode
from clak.views import (
    ListView,
    PprintView,
    ShowView,
    merge_view_settings,
    parse_columns,
    parse_sort_columns,
    resolve_view_width,
)

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
    assert resolve_view_width(width="min", term_width=80, stdout_tty=True) == (
        "min",
        None,
    )
    assert resolve_view_width(width="auto", term_width=80, stdout_tty=True) == (
        "auto",
        80,
    )
    assert resolve_view_width(width="terminal", term_width=80, stdout_tty=True) == (
        "terminal",
        80,
    )
    assert resolve_view_width(width="terminal", term_width=80, stdout_tty=False) == (
        "min",
        None,
    )
    assert resolve_view_width(width="auto", term_width=None, stdout_tty=True) == (
        "min",
        None,
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

    App(parse=False, add_help=False).dispatch(["--width", "min"])

    assert "ada" in capsys.readouterr().out


def test_list_view_mixin_width_cli_option():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    assert "--width" in _option_flags(app)
    app.dispatch(["--width", "auto"])
    settings = getattr(app, "_clak_view_settings", {})
    assert settings.get("width") == "auto"
    assert "term_width" in settings
    assert "stdout_tty" in settings


def test_list_view_mixin_meta_view_width():
    class App(ListViewMixin, Parser):
        class Meta:
            view_width = "min"

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    assert getattr(app, "_clak_view_settings", {}).get("width") == "min"


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
    # Both column flags get the Available: suffix
    assert help_text.count("Available: Var, Value, Order") == 2


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
    assert "not found" in capsys.readouterr().out


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
