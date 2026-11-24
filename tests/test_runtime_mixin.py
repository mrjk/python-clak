"""RuntimeOptMixin: flags, precedence, ctx values and UI integration."""

import io

import pytest

from clak import Parser, RuntimeOptMixin
from clak.comp.runtime import resolve_runtime
from clak.comp.ui import set_ui_settings, ui_policy, ui_session
from clak.core.descriptors import Argument
from clak.exception import ClakUserError
from clak.ui import NO_ANSWER, MappingResponder, Question, UINoInputError, UIPolicy

pytestmark = pytest.mark.tags("unit-tests")


class Tty(io.StringIO):
    def isatty(self):
        return True


TTY = {"stdin": Tty(), "stderr": Tty()}
PIPE = {"stdin": io.StringIO(), "stderr": io.StringIO()}


def rr(args=None, env=None, streams=TTY):
    return resolve_runtime(args or {}, env or {}, **streams)


# resolve_runtime
# ============================


def test_auto_follows_tty():
    assert rr()["interactive"] is True
    assert rr(streams=PIPE)["interactive"] is False
    assert rr()["mode"] == "auto"


def test_ci_forces_never_in_auto():
    assert rr(env={"CI": "true"})["interactive"] is False
    assert rr(env={"CI": "false"})["interactive"] is True
    assert rr(env={"CI": "0"})["interactive"] is True
    assert rr(env={"CI": ""})["interactive"] is True


def test_cli_beats_env_beats_ci():
    # env says never, tty available
    assert rr(env={"CLAK_INTERACTIVE": "never"})["interactive"] is False
    # CLI always beats env never and CI
    assert (
        rr({"interactive": "always"}, {"CLAK_INTERACTIVE": "never", "CI": "1"})[
            "interactive"
        ]
        is True
    )
    # env always beats CI
    assert rr(env={"CLAK_INTERACTIVE": "always", "CI": "1"})["interactive"] is True


def test_explicit_auto_resets_env():
    env = {"CLAK_INTERACTIVE": "never"}
    assert rr({"interactive": "auto"}, env)["interactive"] is True
    # auto still honours CI
    assert rr({"interactive": "auto"}, {"CI": "1"})["interactive"] is False


@pytest.mark.parametrize(
    "raw,expected", [("1", True), ("true", True), ("0", False), ("no", False)]
)
def test_env_boolean_forms(raw, expected):
    assert (
        rr(env={"CLAK_INTERACTIVE": raw}, streams=PIPE if expected else TTY)[
            "interactive"
        ]
        is expected
    )


def test_invalid_env_ignored(caplog):
    with caplog.at_level("WARNING"):
        assert rr(env={"CLAK_INTERACTIVE": "banana"})["interactive"] is True
    assert "banana" in caplog.text


def test_no_input_flag():
    assert rr({"no_input": True})["interactive"] is False
    assert rr({"no_input": True, "interactive": "never"})["interactive"] is False


@pytest.mark.parametrize("when", ["always", "auto"])
def test_no_input_conflict(when):
    with pytest.raises(ClakUserError, match="conflicts"):
        rr({"no_input": True, "interactive": when})


def test_yes_independent_and_no_env():
    assert rr({"yes": True})["assume_yes"] is True
    assert rr({"yes": True})["interactive"] is True
    assert rr(env={"CLAK_YES": "1", "YES": "1"})["assume_yes"] is False


# Parser integration
# ============================


def _app(seen):
    class App(RuntimeOptMixin, Parser):
        class Meta:
            app_name = "rt"

        def cli_run(self, ctx=None, **_):
            seen["interactive"] = ctx.interactive
            seen["assume_yes"] = ctx.assume_yes
            seen["runtime"] = dict(ctx.plugins["runtime"])
            seen["ctx"] = ctx
            return None

    return App(parse=False)


def _run(app, argv):
    args = vars(app.parse_args(argv))
    args.setdefault("__cli_self__", app)
    return app.cli_execute(args)


def test_flags_in_help():
    text = _app({}).parser.format_help()
    for flag in ("--interactive", "--no-input", "-y", "--yes"):
        assert flag in text


def test_ctx_values(monkeypatch):
    monkeypatch.delenv("CLAK_INTERACTIVE", raising=False)
    seen = {}
    _run(_app(seen), ["--no-input", "--yes"])
    assert seen["interactive"] is False
    assert seen["assume_yes"] is True
    assert seen["runtime"]["mode"] == "never"


def test_interactive_choices_validated():
    with pytest.raises(BaseException):
        _app({}).parse_args(["--interactive", "sometimes"])


def test_no_input_conflict_via_parser(monkeypatch):
    monkeypatch.delenv("CLAK_INTERACTIVE", raising=False)
    with pytest.raises(ClakUserError):
        _run(_app({}), ["--no-input", "--interactive", "always"])


def test_ui_session_translates_errors(monkeypatch):
    monkeypatch.delenv("CLAK_INTERACTIVE", raising=False)
    seen = {}
    _run(_app(seen), ["--no-input"])
    ctx = seen["ctx"]
    sess = ui_session(ctx, stdin=io.StringIO(""), stderr=io.StringIO())
    assert sess.text("n", default="d") == "d"
    with pytest.raises(ClakUserError, match="--interactive=always"):
        sess.text("name")
    with pytest.raises(ClakUserError, match="--yes"):
        sess.confirm("delete?", dangerous=True)


def test_ui_policy_fallback_without_mixin():
    class Ctx:
        plugins = {}

    pol = ui_policy(Ctx())
    assert isinstance(pol.interactive, bool)
    assert pol.hint == "" and pol.yes_hint == ""


def test_mixin_fills_ui_settings(monkeypatch):
    monkeypatch.delenv("CLAK_INTERACTIVE", raising=False)
    seen = {}
    _run(_app(seen), ["--no-input"])
    settings = seen["ctx"].ui_settings
    assert settings["interactive"] is False
    assert "--yes" in settings["yes_hint"]
    with pytest.raises(UINoInputError, match="--interactive"):
        ui_policy(seen["ctx"]).answer(Question("text", "n"))


def test_set_ui_settings_merges_and_appends():
    class Ctx:
        plugins = {}

    ctx = Ctx()
    first, second = (lambda q: NO_ANSWER), (lambda q: NO_ANSWER)
    set_ui_settings(ctx, interactive=False, responders=[first])
    settings = set_ui_settings(ctx, hint="h", responders=[second])
    assert settings == {
        "interactive": False,
        "hint": "h",
        "responders": (first, second),
    }


def test_ui_policy_overrides_and_extra_responders():
    class Ctx:
        plugins = {"ui_settings": {"interactive": False}}

    pol = ui_policy(Ctx(), interactive=True, responders=[MappingResponder({"n": "x"})])
    assert pol.interactive is True
    assert pol.answer(Question("text", "n")) == "x"
    assert pol.answer(Question("text", "other")) is NO_ANSWER


def _custom_app(seen):
    class App(Parser):
        class Meta:
            app_name = "custom"

        batch = Argument("--batch", action="store_true", default=False)
        force = Argument("--force", action="store_true", default=False)

        def cli_hook__ui(self, instance, ctx, **_):  # pylint: disable=unused-argument
            set_ui_settings(
                ctx,
                interactive=not ctx.args.batch,
                assume_yes=ctx.args.force,
                hint="drop --batch to allow prompting",
                yes_hint="pass --force",
                stdin=io.StringIO(""),
                stderr=io.StringIO(),
            )

        def cli_run(self, ctx=None, **_):
            seen["ctx"] = ctx

    return App(parse=False)


def test_custom_flags_drive_ui_session():
    seen = {}
    _run(_custom_app(seen), ["--batch"])
    sess = ui_session(seen["ctx"])
    assert sess.text("n", default="d") == "d"
    with pytest.raises(ClakUserError, match="drop --batch"):
        sess.text("name")
    with pytest.raises(ClakUserError, match="--force"):
        sess.confirm("delete?", dangerous=True)

    _run(_custom_app(seen), ["--batch", "--force"])
    assert ui_session(seen["ctx"]).confirm("delete?", dangerous=True) is True


def test_ui_session_explicit_policy():
    class Ctx:
        plugins = {"ui_settings": {"interactive": True}}

    sess = ui_session(Ctx(), policy=UIPolicy.never(), stdin=io.StringIO(""))
    with pytest.raises(ClakUserError):
        sess.text("name")
