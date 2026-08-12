"""Tests for ctx.runtime / clak.runtime."""

from types import SimpleNamespace

import pytest

from clak import Parser
from clak.runtime import (
    COLOR_16,
    COLOR_256,
    COLOR_NONE,
    COLOR_TRUECOLOR,
    RuntimeInfo,
    detect_runtime,
)

pytestmark = pytest.mark.tags("unit-tests")


def _tty(flag: bool):
    return SimpleNamespace(isatty=lambda: flag)


def test_detect_runtime_tty_and_interactive(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(False))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: "/dev/pts/1")
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: "/bin/bash")
    monkeypatch.setattr(
        "clak.runtime._read_parent_exe", lambda _ppid, _cmd: "/bin/bash"
    )

    runtime = detect_runtime()
    assert runtime.stdin_tty is True
    assert runtime.stdout_tty is True
    assert runtime.stderr_tty is False
    assert runtime.interactive is True
    assert runtime.ctty == "/dev/pts/1"
    assert runtime.from_shell is True
    assert runtime.parent_exe == "/bin/bash"


def test_detect_runtime_not_from_shell(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(False))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr(
        "clak.runtime._read_parent_cmd",
        lambda _ppid: "containerd-shim-runc-v2 ...",
    )
    monkeypatch.setattr(
        "clak.runtime._read_parent_exe",
        lambda _ppid, _cmd: "/usr/bin/containerd-shim-runc-v2",
    )

    runtime = detect_runtime()
    assert runtime.interactive is False
    assert runtime.from_shell is False
    assert runtime.ctty is None


def test_color_level_respects_no_color(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(True))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)

    assert detect_runtime().color_level == COLOR_NONE
    assert detect_runtime().color_support is False


def test_color_level_truecolor(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(True))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    monkeypatch.setenv("CLAK_COLORS", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("TERM", "xterm-256color")

    assert detect_runtime().color_level == COLOR_TRUECOLOR


def test_color_level_256_from_term(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(True))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setenv("CLAK_COLORS", "1")
    monkeypatch.setenv("TERM", "xterm-256color")

    assert detect_runtime().color_level == COLOR_256


def test_force_color_without_tty(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(False))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("CLAK_COLORS", "1")

    assert detect_runtime().color_level == COLOR_16


def test_get_size_honors_clak_columns(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(False))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.setenv("CLAK_COLUMNS", "100")
    monkeypatch.setenv("CLAK_LINES", "40")
    monkeypatch.setenv("COLUMNS", "50")
    monkeypatch.setenv("LINES", "20")

    runtime = detect_runtime(narrow_width=120)
    assert runtime.term_width == 100
    assert runtime.term_height == 40
    assert runtime.is_narrow is True
    assert runtime.narrow_width == 120

    monkeypatch.setenv("CLAK_COLUMNS", "130")
    width, height = runtime.get_size()
    assert width == 130
    assert height == 40
    assert runtime.is_narrow is False


def test_narrow_width_from_env(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(False))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(False))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.setenv("CLAK_NARROW_WIDTH", "100")
    monkeypatch.setenv("CLAK_COLUMNS", "90")

    runtime = detect_runtime()
    assert runtime.narrow_width == 100
    assert runtime.is_narrow is True


def test_pager_and_encoding(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(False))
    monkeypatch.setattr(
        "clak.runtime.sys.stdout",
        SimpleNamespace(isatty=lambda: False, encoding="UTF-8"),
    )
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(False))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: None)
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: None)
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: None)
    monkeypatch.setenv("CLAK_PAGER", "less -R")
    monkeypatch.setenv("PAGER", "more")

    runtime = detect_runtime()
    assert runtime.pager == "less -R"
    assert runtime.encoding.lower().replace("-", "") == "utf8"
    assert runtime.unicode_support is True


def test_ctx_runtime_attached_on_dispatch(monkeypatch):
    monkeypatch.setattr("clak.runtime.sys.stdin", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stdout", _tty(True))
    monkeypatch.setattr("clak.runtime.sys.stderr", _tty(True))
    monkeypatch.setattr("clak.runtime._detect_ctty", lambda: "/dev/pts/9")
    monkeypatch.setattr("clak.runtime._read_parent_cmd", lambda _ppid: "/bin/zsh -l")
    monkeypatch.setattr("clak.runtime._read_parent_exe", lambda _ppid, _cmd: "/bin/zsh")

    seen = {}

    class App(Parser):
        class Meta:
            runtime_narrow_width = 100

        def cli_run(self, ctx, **_):
            seen["runtime"] = ctx.runtime
            seen["facts"] = ctx.facts
            seen["narrow"] = ctx.runtime.narrow_width

    App(parse=False).dispatch([])
    assert isinstance(seen["runtime"], RuntimeInfo)
    assert seen["runtime"].from_shell is True
    assert seen["runtime"].interactive is True
    assert seen["narrow"] == 100
    assert seen["facts"] is not None
