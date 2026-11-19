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
