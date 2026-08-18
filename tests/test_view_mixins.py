"""Tests for table view mixins and CLI options."""

import json
import logging

import pytest

from clak import Argument, Command, Parser
from clak.comp.views import ListViewMixin, PprintViewMixin, ShowViewMixin
from clak.views import ListView
from tests.view_fixtures import USERS, USERS_UNSORTED, _option_flags

pytestmark = pytest.mark.tags("unit-tests")


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
    settings = app.ctx.view_settings
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
    assert app.ctx.view_settings.get("width") == "content"


def test_list_view_mixin_wrap_cli_option():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    assert "--wrap" in _option_flags(app)
    app.dispatch(["--wrap", "all"])
    assert app.ctx.view_settings.get("wrap") == "all"


def test_list_view_mixin_meta_view_wrap():
    class App(ListViewMixin, Parser):
        class Meta:
            view_wrap = "all"

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    assert app.ctx.view_settings.get("wrap") == "all"


def test_list_view_mixin_wrap_cli_column_list():
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch(["--wrap", "name,role"])
    assert app.ctx.view_settings.get("wrap") == ["name", "role"]


def test_list_view_mixin_meta_view_wrap_columns_and_min():
    class App(ListViewMixin, Parser):
        class Meta:
            view_wrap = ("name", "city")
            view_wrap_min = {"name": 8}

        def cli_run(self, **_):
            return USERS

    app = App(parse=False, add_help=False)
    app.dispatch([])
    settings = app.ctx.view_settings
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

    settings = app.ctx.view_settings
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
    settings = app.ctx.view_settings
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

    settings = app.ctx.view_settings
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


def test_leaf_list_view_columns_override_root(capsys):
    """Leaf mixin hook rebinds so Meta.view_columns on the child wins."""

    class Leaf(ListViewMixin, Parser):
        "Leaf list."

        class Meta:
            view_columns = ["role"]

        def cli_run(self, **_):
            return USERS

    class Root(ListViewMixin, Parser):
        "Root list."

        class Meta:
            view_columns = ["name"]

        leaf = Command(Leaf)

        def cli_run(self, **_):
            return USERS

    Root(parse=False, add_help=False).dispatch(["leaf"])
    out = capsys.readouterr().out
    assert "admin" in out
    assert "ada" not in out
    assert "London" not in out


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


def test_view_logging_xdg_mixin_composition():
    """View mixin leftmost still runs logging and XDG add_arguments."""
    from clak.comp.config import XDGConfigMixin
    from clak.comp.logging import LoggingOptMixin

    class App(ListViewMixin, LoggingOptMixin, XDGConfigMixin, Parser):
        class Meta:
            app_name = "demo-app"
            log_colors_env = "DEMO_LOG_COLORS"

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    flags = _option_flags(app)
    assert "--columns" in flags
    assert "-v" in flags
    assert "--conf-file" in flags
    help_text = app.parser.format_help()
    assert "DEMO_LOG_COLORS" in help_text
    conf = next(a.default for a in app.parser._actions if a.dest == "xdg_config")
    assert "demo-app" in str(conf)
