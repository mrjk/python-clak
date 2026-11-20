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
from functools import cached_property
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
    return {name: gid for gid in gids if (name := _group_name(gid))}


class IdentityInfo:
    """Real or effective process identity (ids eager, NSS names lazy)."""

    def __init__(  # pylint: disable=too-many-arguments
        self, facts: "FactsInfo", *, uid, gid, group_ids, label
    ):
        self._facts = facts
        self._label = label
        self.uid = uid
        self.gid = gid
        self.group_ids = list(group_ids)

    @cached_property
    def _names(self):
        return self._facts.run_blocking(
            f"NSS identity resolve ({self._label})",
            lambda: (
                _user_name(self.uid),
                _group_name(self.gid),
                _groups_map(self.group_ids),
            ),
            fallback=(None, None, {}),
        )

    @property
    def user_name(self) -> Optional[str]:
        """Resolved user name for ``uid``, or None."""
        return self._names[0]

    @property
    def group_name(self) -> Optional[str]:
        """Resolved primary group name for ``gid``, or None."""
        return self._names[1]

    @property
    def groups(self) -> Dict[str, int]:
        """Map of supplemental group name to gid."""
        return dict(self._names[2])

    def clear_names(self) -> None:
        """Drop cached NSS name lookups."""
        self.__dict__.pop("_names", None)


def _identity_shortcut(attr: str, doc: str) -> property:
    return property(lambda self: getattr(self.identity, attr), doc=doc)


class FactsInfo:
    """Lazy OS/process facts attached as ``ctx.facts``."""

    _CACHED = ("hostname", "_fqdn_domain", "distro", "identity", "running")

    def __init__(self, timeout: Optional[float] = _UNSET):
        if timeout is _UNSET:
            timeout = parse_facts_timeout()
        self._timeout = None if timeout is not None and timeout < 0 else timeout

    def clear_cache(self) -> None:
        """Drop all cached fact values."""
        for name in self._CACHED:
            value = self.__dict__.pop(name, None)
            if isinstance(value, IdentityInfo):
                value.clear_names()

    def run_blocking(self, what: str, fn: Callable[[], T], fallback: T) -> T:
        """Run *fn* with timeout; return *fallback* on skip, timeout, or error."""
        timeout = self._timeout
        logger.info("%s starting", what)
        if timeout == 0:
            logger.warning("%s skipped (CLAK_FACTS_TIMEOUT=0)", what)
            return fallback
        try:
            if timeout is None:
                result = fn()
            else:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(fn).result(timeout=timeout)
        except FuturesTimeout:
            logger.warning("%s timed out after %ss", what, timeout)
            return fallback
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.debug("%s failed: %s", what, err)
            return fallback
        logger.debug("%s finished: %r", what, result)
        return result

    @cached_property
    def hostname(self) -> str:
        """Short hostname from ``socket.gethostname``."""
        try:
            return socket.gethostname()
        except OSError:
            return ""

    @cached_property
    def _fqdn_domain(self) -> tuple:
        host = self.hostname
        fqdn = (
            self.run_blocking(
                f"DNS / FQDN resolution for hostname={host!r}",
                socket.getfqdn,
                fallback=host,
            )
            or host
        )
        return fqdn, _domain_from_fqdn(fqdn, host)

    @property
    def fqdn(self) -> str:
        """Fully qualified domain name (lazy DNS)."""
        return self._fqdn_domain[0]

    @property
    def domain(self) -> Optional[str]:
        """Domain portion of ``fqdn``, or None."""
        return self._fqdn_domain[1]

    @cached_property
    def distro(self) -> Dict[str, str]:
        """Parsed ``/etc/os-release`` fields."""
        return parse_os_release()

    @property
    def distro_id(self) -> Optional[str]:
        """``ID`` from os-release."""
        return self.distro.get("ID")

    @property
    def distro_name(self) -> Optional[str]:
        """Pretty or short distro name from os-release."""
        return self.distro.get("PRETTY_NAME") or self.distro.get("NAME")

    @property
    def distro_version(self) -> Optional[str]:
        """Version id or version string from os-release."""
        return self.distro.get("VERSION_ID") or self.distro.get("VERSION")

    @property
    def distro_like(self) -> Optional[str]:
        """``ID_LIKE`` from os-release."""
        return self.distro.get("ID_LIKE")

    def _build_identity(self, *, effective: bool) -> IdentityInfo:
        label = "effective" if effective else "real"
        if not hasattr(os, "getuid"):
            return IdentityInfo(self, uid=-1, gid=-1, group_ids=[], label=label)
        uid, gid = (
            (os.geteuid(), os.getegid()) if effective else (os.getuid(), os.getgid())
        )
        try:
            gids = list(os.getgroups())
        except OSError:
            gids = []
        if gid not in gids:
            gids = [gid] + gids
        return IdentityInfo(self, uid=uid, gid=gid, group_ids=gids, label=label)

    @cached_property
    def identity(self) -> IdentityInfo:
        """Real (uid/gid) identity bundle."""
        return self._build_identity(effective=False)

    @cached_property
    def running(self) -> IdentityInfo:
        """Effective (euid/egid) identity bundle."""
        return self._build_identity(effective=True)

    uid = _identity_shortcut("uid", "Real user id.")
    gid = _identity_shortcut("gid", "Real group id.")
    group_ids = _identity_shortcut("group_ids", "Real supplemental group ids.")
    user_name = _identity_shortcut("user_name", "Real user name (lazy NSS).")
    group_name = _identity_shortcut("group_name", "Real primary group name.")
    groups = _identity_shortcut("groups", "Real supplemental groups map.")

    def __repr__(self) -> str:
        return f"FactsInfo(timeout={self._timeout!r})"


def detect_facts(timeout: Optional[float] = _UNSET) -> FactsInfo:
    """Return a facts shell; field resolution stays lazy."""
    return FactsInfo(timeout=timeout)
