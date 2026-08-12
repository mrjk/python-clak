"""Optional OS/process facts sugar attached as ``ctx.facts``.

Almost out of topic for Clak; provided as lazy helpers for apps.
Blocking resolves (FQDN, NSS names) log INFO first and honor
``CLAK_FACTS_TIMEOUT`` (default 30s; ``0`` skip; ``-1`` no timeout).
"""

from __future__ import annotations

import logging
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("clak.facts")

DEFAULT_FACTS_TIMEOUT = 30.0
_UNSET = object()
T = TypeVar("T")

try:
    import grp
    import pwd
except ImportError:  # pragma: no cover - non-Unix
    pwd = None  # type: ignore
    grp = None  # type: ignore


def parse_facts_timeout(raw: Optional[str] = _UNSET) -> Optional[float]:
    """Return timeout seconds, or None for no timeout.

    Unset/empty -> 30s default.
    ``0`` -> 0 (skip blocking resolve).
    ``-1`` -> None (wait forever).
    """
    if raw is _UNSET:
        raw = os.environ.get("CLAK_FACTS_TIMEOUT")
    if raw is None or raw == "":
        return DEFAULT_FACTS_TIMEOUT
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_FACTS_TIMEOUT
    if value < 0:
        return None
    return value


def parse_os_release(path: str = "/etc/os-release") -> Dict[str, str]:
    """Parse ``/etc/os-release`` into a key/value dict."""
    data: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return data

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        data[key] = value
    return data


def _domain_from_fqdn(fqdn: str, hostname: str) -> Optional[str]:
    if not fqdn or "." not in fqdn:
        return None
    if fqdn == hostname:
        return None
    return fqdn.split(".", 1)[1] or None


def _group_name(gid: int) -> Optional[str]:
    if grp is None:
        return None
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return None


def _user_name(uid: int) -> Optional[str]:
    if pwd is None:
        return None
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return None


def _groups_map(gids: List[int]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for gid in gids:
        name = _group_name(gid)
        if name:
            out[name] = gid
    return out


class IdentityInfo:
    """Real or effective process identity (numeric eager-on-bundle, names lazy)."""

    __slots__ = (
        "uid",
        "gid",
        "group_ids",
        "_user_name",
        "_group_name",
        "_groups",
        "_names_loaded",
        "_facts",
        "_label",
    )

    def __init__(
        self,
        facts: "FactsInfo",
        *,
        uid: int,
        gid: int,
        group_ids: List[int],
        label: str,
    ):
        self._facts = facts
        self._label = label
        self.uid = uid
        self.gid = gid
        self.group_ids = list(group_ids)
        self._user_name = _UNSET
        self._group_name = _UNSET
        self._groups = _UNSET
        self._names_loaded = False

    def _ensure_names(self) -> None:
        if self._names_loaded:
            return
        self._names_loaded = True

        def resolve():
            return (
                _user_name(self.uid),
                _group_name(self.gid),
                _groups_map(self.group_ids),
            )

        result = self._facts._run_blocking(
            f"NSS identity resolve ({self._label})",
            resolve,
            fallback=(None, None, {}),
        )
        self._user_name, self._group_name, self._groups = result

    @property
    def user_name(self) -> Optional[str]:
        self._ensure_names()
        return None if self._user_name is _UNSET else self._user_name  # type: ignore

    @property
    def group_name(self) -> Optional[str]:
        self._ensure_names()
        return None if self._group_name is _UNSET else self._group_name  # type: ignore

    @property
    def groups(self) -> Dict[str, int]:
        self._ensure_names()
        if self._groups is _UNSET:
            return {}
        return dict(self._groups)  # type: ignore

    def clear_names(self) -> None:
        self._user_name = _UNSET
        self._group_name = _UNSET
        self._groups = _UNSET
        self._names_loaded = False


class FactsInfo:
    """Lazy OS/process facts attached as ``ctx.facts``."""

    __slots__ = (
        "_timeout",
        "_hostname",
        "_fqdn",
        "_domain",
        "_distro",
        "_identity",
        "_running",
    )

    def __init__(self, timeout: Optional[float] = _UNSET):
        if timeout is _UNSET:
            self._timeout = parse_facts_timeout()
        elif timeout is not None and timeout < 0:
            self._timeout = None
        else:
            self._timeout = timeout
        self._hostname = _UNSET
        self._fqdn = _UNSET
        self._domain = _UNSET
        self._distro = _UNSET
        self._identity = _UNSET
        self._running = _UNSET

    def clear_cache(self) -> None:
        """Drop all cached fact values."""
        self._hostname = _UNSET
        self._fqdn = _UNSET
        self._domain = _UNSET
        self._distro = _UNSET
        if self._identity is not _UNSET:
            self._identity.clear_names()  # type: ignore
        if self._running is not _UNSET:
            self._running.clear_names()  # type: ignore
        self._identity = _UNSET
        self._running = _UNSET

    def _run_blocking(
        self,
        what: str,
        fn: Callable[[], T],
        fallback: T,
    ) -> T:
        timeout = self._timeout
        logger.info("%s starting", what)
        if timeout == 0:
            logger.warning("%s skipped (CLAK_FACTS_TIMEOUT=0)", what)
            return fallback

        if timeout is None:
            try:
                result = fn()
            except Exception as err:  # pylint: disable=broad-exception-caught
                logger.debug("%s failed: %s", what, err)
                return fallback
            logger.debug("%s finished: %r", what, result)
            return result

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn)
            try:
                result = future.result(timeout=timeout)
            except FuturesTimeout:
                logger.warning("%s timed out after %ss", what, timeout)
                return fallback
            except Exception as err:  # pylint: disable=broad-exception-caught
                logger.debug("%s failed: %s", what, err)
                return fallback
        logger.debug("%s finished: %r", what, result)
        return result

    @property
    def hostname(self) -> str:
        if self._hostname is _UNSET:
            try:
                self._hostname = socket.gethostname()
            except OSError:
                self._hostname = ""
        return self._hostname  # type: ignore

    def _ensure_fqdn(self) -> None:
        if self._fqdn is not _UNSET:
            return
        host = self.hostname
        fqdn = self._run_blocking(
            f"DNS / FQDN resolution for hostname={host!r}",
            socket.getfqdn,
            fallback=host,
        )
        self._fqdn = fqdn or host
        self._domain = _domain_from_fqdn(self._fqdn, host)

    @property
    def fqdn(self) -> str:
        self._ensure_fqdn()
        return self._fqdn  # type: ignore

    @property
    def domain(self) -> Optional[str]:
        self._ensure_fqdn()
        return self._domain  # type: ignore

    def _ensure_distro(self) -> Dict[str, str]:
        if self._distro is _UNSET:
            self._distro = parse_os_release()
        return self._distro  # type: ignore

    @property
    def distro(self) -> Dict[str, str]:
        return dict(self._ensure_distro())

    @property
    def distro_id(self) -> Optional[str]:
        return self._ensure_distro().get("ID")

    @property
    def distro_name(self) -> Optional[str]:
        data = self._ensure_distro()
        return data.get("PRETTY_NAME") or data.get("NAME")

    @property
    def distro_version(self) -> Optional[str]:
        data = self._ensure_distro()
        return data.get("VERSION_ID") or data.get("VERSION")

    @property
    def distro_like(self) -> Optional[str]:
        return self._ensure_distro().get("ID_LIKE")

    def _build_identity(self, *, effective: bool) -> IdentityInfo:
        if not hasattr(os, "getuid"):
            return IdentityInfo(
                self, uid=-1, gid=-1, group_ids=[], label="effective" if effective else "real"
            )
        if effective:
            uid = os.geteuid()
            gid = os.getegid()
            label = "effective"
        else:
            uid = os.getuid()
            gid = os.getgid()
            label = "real"
        gids = []
        try:
            gids = list(os.getgroups())
        except OSError:
            gids = []
        if gid not in gids:
            gids = [gid] + gids
        return IdentityInfo(self, uid=uid, gid=gid, group_ids=gids, label=label)

    def _ensure_identity(self) -> IdentityInfo:
        if self._identity is _UNSET:
            self._identity = self._build_identity(effective=False)
        return self._identity  # type: ignore

    def _ensure_running(self) -> IdentityInfo:
        if self._running is _UNSET:
            self._running = self._build_identity(effective=True)
        return self._running  # type: ignore

    @property
    def uid(self) -> int:
        return self._ensure_identity().uid

    @property
    def gid(self) -> int:
        return self._ensure_identity().gid

    @property
    def group_ids(self) -> List[int]:
        return list(self._ensure_identity().group_ids)

    @property
    def user_name(self) -> Optional[str]:
        return self._ensure_identity().user_name

    @property
    def group_name(self) -> Optional[str]:
        return self._ensure_identity().group_name

    @property
    def groups(self) -> Dict[str, int]:
        return self._ensure_identity().groups

    @property
    def running(self) -> IdentityInfo:
        return self._ensure_running()

    def __repr__(self) -> str:
        return f"FactsInfo(timeout={self._timeout!r})"


def detect_facts(timeout: Optional[float] = _UNSET) -> FactsInfo:
    """Return a facts shell; field resolution stays lazy."""
    return FactsInfo(timeout=timeout)
