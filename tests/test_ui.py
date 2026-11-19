import io

import pytest

from clak.ui import ChoicePrompt, ConfirmPrompt, ContinuePrompt, TextPrompt, UIAbort, WaitSpinner


def io_(text):
    return {"stdin": io.StringIO(text), "stderr": io.StringIO()}


def test_prompt_default_cast_retry():
    assert TextPrompt("n", default=3, cast=int, **io_("\n")).ask() == 3
    assert TextPrompt("n", cast=int, **io_("x\n7\n")).ask() == 7


def test_prompt_abort():
    with pytest.raises(UIAbort):
        TextPrompt("n", **io_("")).ask()
    with pytest.raises(UIAbort):
        TextPrompt("n", max_tries=2, **io_("\n\n")).ask()


def test_confirm():
    assert ConfirmPrompt("ok?", **io_("y\n")).ask() is True
    assert ConfirmPrompt("ok?", default=False, **io_("\n")).ask() is False
    assert ConfirmPrompt("ok?", **io_("maybe\nno\n")).ask() is False


def test_choice():
    assert ChoicePrompt("pick", ["a", "b"], **io_("2\n")).ask() == "b"
    assert ChoicePrompt("pick", ["a", "b"], **io_("a\n")).ask() == "a"


def test_continue():
    assert ContinuePrompt(interactive=False, **io_("")).ask() is True
    assert ContinuePrompt(interactive=True, **io_("\n")).ask() is True
    assert ContinuePrompt(interactive=True, **io_("q\n")).ask() is False
    with pytest.raises(UIAbort):
        ContinuePrompt(interactive=True, raise_on_quit=True, **io_("q\n")).ask()


def test_wait_non_interactive():
    kw = io_("")
    with WaitSpinner("Loading", interactive=False, **kw):
        pass
    assert "Loading... done" in kw["stderr"].getvalue()


# Policy
# ============================

from clak.ui import (  # noqa: E402  pylint: disable=wrong-import-position
    NO_ANSWER,
    ChoicePrompt as _Choice,
    DefaultsResponder,
    MappingResponder,
    Question,
    TextPrompt as _Text,
    UINoInputError,
    UIPolicy,
    UISession,
    YesResponder,
    detect_interactive,
)


class _NoRead(io.StringIO):
    """stdin that fails the test if anything reads from it."""

    def readline(self, *a, **k):  # pylint: disable=arguments-differ
        raise AssertionError("stdin must not be read")


class _Tty(io.StringIO):
    def isatty(self):
        return True


def _never(**kw):
    return {"stdin": _NoRead(), "stderr": io.StringIO(), **kw}


def test_responders():
    q = Question("confirm", "ok?")
    assert YesResponder()(q) is True
    assert YesResponder()(Question("text", "n")) is NO_ANSWER
    assert DefaultsResponder()(q) is NO_ANSWER
    assert DefaultsResponder()(Question("confirm", "ok?", default=False)) is False
    assert DefaultsResponder()(Question("text", "n", required=False)) is None
    assert DefaultsResponder()(Question("confirm", "x", default=True, dangerous=True)) is NO_ANSWER
    assert MappingResponder({"a": 1})(Question("text", "a")) == 1
    assert MappingResponder({})(Question("text", "a")) is NO_ANSWER


def test_never_uses_defaults_without_reading():
    pol = UIPolicy.never()
    assert _Text("n", default="x", policy=pol, **_never()).ask() == "x"
    assert ConfirmPrompt("ok?", default=False, policy=pol, **_never()).ask() is False
    assert _Choice("c", ["a", "b"], default="b", policy=pol, **_never()).ask() == "b"
    assert _Text("n", required=False, policy=pol, **_never()).ask() is None


def test_never_without_default_raises():
    pol = UIPolicy.never()
    with pytest.raises(UINoInputError, match="input required: n"):
        _Text("n", policy=pol, **_never()).ask()
    with pytest.raises(UINoInputError):
        ConfirmPrompt("ok?", policy=pol, **_never()).ask()
    with pytest.raises(UINoInputError):
        _Choice("c", ["a"], policy=pol, **_never()).ask()


def test_hint_in_error():
    pol = UIPolicy.build(False, hint="use --interactive", yes_hint="pass --yes")
    with pytest.raises(UINoInputError, match=r"\(use --interactive\)"):
        _Text("n", policy=pol, **_never()).ask()
    with pytest.raises(UINoInputError, match=r"\(pass --yes\)"):
        ConfirmPrompt("del?", dangerous=True, default=True, policy=pol, **_never()).ask()


def test_assume_yes():
    pol = UIPolicy.never(assume_yes=True)
    assert ConfirmPrompt("ok?", policy=pol, **_never()).ask() is True
    assert ConfirmPrompt("del?", dangerous=True, policy=pol, **_never()).ask() is True
    # yes does not answer other kinds
    with pytest.raises(UINoInputError):
        _Text("n", policy=pol, **_never()).ask()


def test_always_reads_and_yes_skips_confirm():
    pol = UIPolicy.always()
    assert _Text("n", policy=pol, **io_("ada\n")).ask() == "ada"
    pol = UIPolicy.always(assume_yes=True)
    assert ConfirmPrompt("ok?", policy=pol, **_never()).ask() is True


def test_continue_and_spinner_follow_policy():
    assert ContinuePrompt(policy=UIPolicy.never(), **_never()).ask() is True
    kw = io_("")
    with WaitSpinner("Loading", policy=UIPolicy.never(), **kw):
        pass
    assert "Loading... done" in kw["stderr"].getvalue()


def test_session_binds_policy():
    ui = UISession(UIPolicy.never(assume_yes=True), stdin=_NoRead(), stderr=io.StringIO())
    assert ui.confirm("ok?") is True
    assert ui.text("n", default="d") == "d"
    assert ui.choice("c", ["a", "b"], default="a") == "a"
    assert ui.pause() is True


def test_detect_interactive():
    assert detect_interactive(_Tty(), _Tty(), {}) is True
    assert detect_interactive(io.StringIO(), _Tty(), {}) is False
    assert detect_interactive(_Tty(), io.StringIO(), {}) is False
    assert detect_interactive(_Tty(), _Tty(), {"CI": "true"}) is False
    assert detect_interactive(_Tty(), _Tty(), {"CI": "1"}) is False
    for off in ("", "0", "false", "False", "no"):
        assert detect_interactive(_Tty(), _Tty(), {"CI": off}) is True
