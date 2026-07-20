"""Tests for public CLI views, mixins, and parser integration."""

import json
import logging

import pytest

from clak.comp.views import ListViewMixin, PprintViewMixin, ShowViewMixin
from clak.parser import Command, Parser, ParserNode
from clak.views import (
    ListView,
    PprintView,
    ShowView,
    merge_view_settings,
    parse_columns,
    parse_sort_columns,
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
    assert parse_columns("0, 2") == [0, 2]
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

    App(parse=False, add_help=False).dispatch(["--width", "40"])

    assert "ada" in capsys.readouterr().out


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


# ---------------------------------------------------------------------------
# Mixins — output format (Cliff-style)
# ---------------------------------------------------------------------------


def test_list_view_mixin_format_json(capsys):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    App(parse=False, add_help=False).dispatch(["--format", "json", "--columns", "name,role"])

    out = capsys.readouterr().out
    records = json.loads(out)
    assert records == [
        {"name": "ada", "role": "admin"},
        {"name": "linus", "role": "dev"},
    ]


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

    App(parse=False, add_help=False).dispatch(
        ["--format", "yaml", "--columns", "name"]
    )

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

    assert getattr(app, "_clak_view_settings", None) == {
        "format": "json",
        "columns": ["name", "role"],
    }
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

    assert getattr(app, "_clak_view_settings", None) == {
        "columns": ["name", "role"]
    }
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
