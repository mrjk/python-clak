"""Core CLI runtime snapshot: TTY, launch context, display, terminal size.

Attached as ``ctx.runtime`` for Clak internals and user ``cli_run`` / hooks.
Local-only detection; no DNS or NSS.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from typing import Optional, Tuple

from clak.common import to_boolean
from clak.settings import CLAK_COLORS

logger = logging.getLogger("clak.runtime")

DEFAULT_NARROW_WIDTH = 80
DEFAULT_TERM_WIDTH = 80
DEFAULT_TERM_HEIGHT = 24

SHELL_NAMES = frozenset(
    {
        "bash",
        "sh",
        "zsh",
        "fish",
        "dash",
        "ksh",
        "csh",
        "tcsh",
        "ash",
        "pwsh",
        "powershell",
    }
)

COLOR_NONE = "none"
COLOR_16 = "16"
COLOR_256 = "256"
COLOR_TRUECOLOR = "truecolor"


def _env_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _resolve_narrow_width(narrow_width: Optional[int] = None) -> int:
    if narrow_width is not None:
        return int(narrow_width)
    env = _env_int("CLAK_NARROW_WIDTH")
    if env is not None:
        return env
    return DEFAULT_NARROW_WIDTH


def _stream_isatty(stream) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _detect_ctty() -> Optional[str]:
    """Return controlling terminal device path, or None."""
    try:
        fd = os.open("/dev/tty", os.O_RDONLY | os.O_NOCTTY)
    except OSError:
        return None
    try:
        return os.ttyname(fd)
    except OSError:
        return None
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _read_parent_cmd(ppid: int) -> Optional[str]:
    path = f"/proc/{ppid}/cmdline"
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    if not raw:
        return None
    text = raw.replace(b"\0", b" ").decode(errors="replace").strip()
    return text or None


def _read_parent_exe(ppid: int, parent_cmd: Optional[str]) -> Optional[str]:
    exe_path = f"/proc/{ppid}/exe"
    try:
        return os.path.realpath(exe_path)
    except OSError:
        pass
    if parent_cmd:
        argv0 = parent_cmd.split(None, 1)[0]
        return argv0 or None
    return None


def _from_shell(parent_exe: Optional[str]) -> bool:
    if not parent_exe:
        return False
    name = os.path.basename(parent_exe)
    if name.endswith(" (deleted)"):
        name = name[: -len(" (deleted)")]
    return name in SHELL_NAMES


def _stdout_encoding() -> str:
    encoding = getattr(sys.stdout, "encoding", None) or ""
    encoding = encoding.strip() or "utf-8"
    return encoding


def _unicode_support(encoding: str) -> bool:
    normalized = encoding.lower().replace("-", "").replace("_", "")
    return normalized in {"utf8", "utf16", "utf32"} or normalized.startswith(
        ("utf8", "utf16", "utf32")
    )


def _force_color_level() -> Optional[str]:
    for name in ("FORCE_COLOR", "CLICOLOR_FORCE"):
        raw = os.environ.get(name)
        if raw is None or raw == "":
            continue
        if raw in {"0", "false", "False"}:
            return COLOR_NONE
        if raw in {"3", "truecolor", "24bit"}:
            return COLOR_TRUECOLOR
        if raw in {"2", "256"}:
            return COLOR_256
        return COLOR_16
    return None


def _detect_color_level(stdout_tty: bool) -> str:
    if os.environ.get("NO_COLOR"):
        return COLOR_NONE

    raw_clak_colors = os.environ.get("CLAK_COLORS")
    if raw_clak_colors is not None:
        try:
            if not to_boolean(raw_clak_colors):
                return COLOR_NONE
        except ValueError:
            pass
    elif not CLAK_COLORS:
        return COLOR_NONE

    forced = _force_color_level()
    if forced is not None:
        return forced

    if not stdout_tty:
        return COLOR_NONE

    term = (os.environ.get("TERM") or "").lower()
    if term in {"", "dumb"}:
        return COLOR_NONE

    colorterm = (os.environ.get("COLORTERM") or "").lower()
    if colorterm in {"truecolor", "24bit"}:
        return COLOR_TRUECOLOR
    if "256" in term or term.endswith("256color"):
        return COLOR_256
    return COLOR_16


def _hyperlinks_support(stdout_tty: bool) -> bool:
    if not stdout_tty:
        return False
    term = (os.environ.get("TERM") or "").lower()
    if term in {"", "dumb"}:
        return False

    term_program = os.environ.get("TERM_PROGRAM") or ""
    if term_program in {"iTerm.app", "WezTerm", "vscode", "ghostty"}:
        return True
    if os.environ.get("WT_SESSION"):
        return True

    vte = os.environ.get("VTE_VERSION")
    if vte:
        try:
            if int(vte) >= 4600:
                return True
        except ValueError:
            pass

    colorterm = (os.environ.get("COLORTERM") or "").lower()
    if colorterm in {"truecolor", "24bit"}:
        return True
    return False


def _resolve_pager() -> Optional[str]:
    for name in ("CLAK_PAGER", "PAGER"):
        value = os.environ.get(name)
        if value:
            return value
    return None


class RuntimeInfo:
    """Eager CLI/session snapshot attached as ``ctx.runtime``."""

    __slots__ = (
        "stdin_tty",
        "stdout_tty",
        "stderr_tty",
        "interactive",
        "ctty",
        "from_shell",
        "parent_ppid",
        "parent_exe",
        "parent_cmd",
        "encoding",
        "color_level",
        "color_support",
        "unicode_support",
        "hyperlinks_support",
        "pager",
        "term_width",
        "term_height",
        "narrow_width",
        "is_narrow",
    )

    def __init__(
        self,
        *,
        stdin_tty: bool,
        stdout_tty: bool,
        stderr_tty: bool,
        ctty: Optional[str],
        from_shell: bool,
        parent_ppid: int,
        parent_exe: Optional[str],
        parent_cmd: Optional[str],
        encoding: str,
        color_level: str,
        unicode_support: bool,
        hyperlinks_support: bool,
        pager: Optional[str],
        narrow_width: int,
    ):
        self.stdin_tty = stdin_tty
        self.stdout_tty = stdout_tty
        self.stderr_tty = stderr_tty
        self.interactive = bool(stdin_tty and stdout_tty)
        self.ctty = ctty
        self.from_shell = from_shell
        self.parent_ppid = parent_ppid
        self.parent_exe = parent_exe
        self.parent_cmd = parent_cmd
        self.encoding = encoding
        self.color_level = color_level
        self.color_support = color_level != COLOR_NONE
        self.unicode_support = unicode_support
        self.hyperlinks_support = hyperlinks_support
        self.pager = pager
        self.narrow_width = int(narrow_width)
        self.term_width = DEFAULT_TERM_WIDTH
        self.term_height = DEFAULT_TERM_HEIGHT
        self.is_narrow = True
        self.get_size()

    def get_size(self) -> Tuple[int, int]:
        """Refresh terminal size; honors CLAK_COLUMNS/LINES then COLUMNS/LINES."""
        size = shutil.get_terminal_size(
            fallback=(DEFAULT_TERM_WIDTH, DEFAULT_TERM_HEIGHT)
        )
        width, height = int(size.columns), int(size.lines)

        clak_cols = _env_int("CLAK_COLUMNS")
        clak_lines = _env_int("CLAK_LINES")
        if clak_cols is not None:
            width = clak_cols
        if clak_lines is not None:
            height = clak_lines

        self.term_width = width
        self.term_height = height
        self.is_narrow = width < self.narrow_width
        return self.term_width, self.term_height

    def __repr__(self) -> str:
        return (
            f"RuntimeInfo(interactive={self.interactive!r}, "
            f"from_shell={self.from_shell!r}, "
            f"color_level={self.color_level!r}, "
            f"term_width={self.term_width!r})"
        )


def detect_runtime(narrow_width: Optional[int] = None) -> RuntimeInfo:
    """Build an eager local runtime snapshot (no DNS/NSS)."""
    stdin_tty = _stream_isatty(sys.stdin)
    stdout_tty = _stream_isatty(sys.stdout)
    stderr_tty = _stream_isatty(sys.stderr)
    parent_ppid = os.getppid()
    parent_cmd = _read_parent_cmd(parent_ppid)
    parent_exe = _read_parent_exe(parent_ppid, parent_cmd)
    encoding = _stdout_encoding()
    color_level = _detect_color_level(stdout_tty)

    return RuntimeInfo(
        stdin_tty=stdin_tty,
        stdout_tty=stdout_tty,
        stderr_tty=stderr_tty,
        ctty=_detect_ctty(),
        from_shell=_from_shell(parent_exe),
        parent_ppid=parent_ppid,
        parent_exe=parent_exe,
        parent_cmd=parent_cmd,
        encoding=encoding,
        color_level=color_level,
        unicode_support=_unicode_support(encoding),
        hyperlinks_support=_hyperlinks_support(stdout_tty),
        pager=_resolve_pager(),
        narrow_width=_resolve_narrow_width(narrow_width),
    )
