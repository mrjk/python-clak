"""Tests for ctx.facts / clak.facts."""

import logging
import time

import pytest

from clak.facts import (
    DEFAULT_FACTS_TIMEOUT,
    FactsInfo,
    detect_facts,
    parse_facts_timeout,
    parse_os_release,
)

pytestmark = pytest.mark.tags("unit-tests")


def test_parse_facts_timeout_defaults():
    assert parse_facts_timeout(None) == DEFAULT_FACTS_TIMEOUT
    assert parse_facts_timeout("") == DEFAULT_FACTS_TIMEOUT
    assert parse_facts_timeout("30") == 30.0
    assert parse_facts_timeout("0") == 0.0
    assert parse_facts_timeout("-1") is None
    assert parse_facts_timeout("nope") == DEFAULT_FACTS_TIMEOUT


def test_detect_facts_is_lazy_shell():
    from clak.facts import _UNSET

    facts = detect_facts(timeout=-1)
    assert isinstance(facts, FactsInfo)
    assert facts._hostname is _UNSET  # noqa: SLF001
    assert facts._fqdn is _UNSET  # noqa: SLF001
    assert facts._distro is _UNSET  # noqa: SLF001
    assert facts._identity is _UNSET  # noqa: SLF001


def test_detect_facts_does_not_resolve_until_access(monkeypatch):
    calls = {"fqdn": 0, "host": 0}

    def boom_fqdn():
        calls["fqdn"] += 1
        return "host.example.com"

    def boom_host():
        calls["host"] += 1
        return "host"

    monkeypatch.setattr("clak.runtime.facts.socket.getfqdn", boom_fqdn)
    monkeypatch.setattr("clak.runtime.facts.socket.gethostname", boom_host)

    facts = detect_facts(timeout=-1)
    assert calls["fqdn"] == 0
    assert calls["host"] == 0
    assert facts.hostname == "host"
    assert calls["host"] == 1
    assert calls["fqdn"] == 0
    assert facts.fqdn == "host.example.com"
    assert calls["fqdn"] == 1
    assert facts.domain == "example.com"
    assert facts.fqdn == "host.example.com"
    assert calls["fqdn"] == 1


def test_fqdn_logs_info(monkeypatch, caplog):
    monkeypatch.setattr("clak.runtime.facts.socket.gethostname", lambda: "box")
    monkeypatch.setattr("clak.runtime.facts.socket.getfqdn", lambda: "box.example.com")

    facts = detect_facts(timeout=-1)
    with caplog.at_level(logging.INFO, logger="clak.facts"):
        _ = facts.fqdn
    assert any(
        "FQDN" in record.message or "DNS" in record.message for record in caplog.records
    )


def test_facts_timeout_zero_skips_blocking(monkeypatch):
    monkeypatch.setattr("clak.runtime.facts.socket.gethostname", lambda: "box")

    def never():
        raise AssertionError("getfqdn should not run")

    monkeypatch.setattr("clak.runtime.facts.socket.getfqdn", never)
    facts = detect_facts(timeout=0)
    assert facts.fqdn == "box"
    assert facts.domain is None


def test_facts_timeout_soft_fallback(monkeypatch):
    monkeypatch.setattr("clak.runtime.facts.socket.gethostname", lambda: "box")

    def slow():
        time.sleep(0.2)
        return "box.example.com"

    monkeypatch.setattr("clak.runtime.facts.socket.getfqdn", slow)
    facts = detect_facts(timeout=0.05)
    assert facts.fqdn == "box"
    assert facts.domain is None


def test_parse_os_release(tmp_path):
    path = tmp_path / "os-release"
    path.write_text(
        'NAME="Manjaro Linux"\n'
        "ID=manjaro\n"
        'ID_LIKE="arch"\n'
        "VERSION_ID=24.0\n"
        'PRETTY_NAME="Manjaro Linux"\n',
        encoding="utf-8",
    )
    data = parse_os_release(str(path))
    assert data["ID"] == "manjaro"
    assert data["ID_LIKE"] == "arch"
    assert data["VERSION_ID"] == "24.0"

    facts = detect_facts(timeout=-1)
    facts._distro = data  # noqa: SLF001
    assert facts.distro_id == "manjaro"
    assert facts.distro_like == "arch"
    assert facts.distro_version == "24.0"
    assert "Manjaro" in (facts.distro_name or "")


def test_clear_cache(monkeypatch):
    hosts = iter(["one", "two"])
    monkeypatch.setattr("clak.runtime.facts.socket.gethostname", lambda: next(hosts))
    facts = detect_facts(timeout=-1)
    assert facts.hostname == "one"
    facts.clear_cache()
    assert facts.hostname == "two"


def test_identity_numeric_without_nss_names(monkeypatch):
    monkeypatch.setattr("clak.runtime.facts.os.getuid", lambda: 1000, raising=False)
    monkeypatch.setattr("clak.runtime.facts.os.getgid", lambda: 1000, raising=False)
    monkeypatch.setattr("clak.runtime.facts.os.geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr("clak.runtime.facts.os.getegid", lambda: 1000, raising=False)
    monkeypatch.setattr("clak.runtime.facts.os.getgroups", lambda: [1000, 10])

    # Avoid real NSS in this unit test for names path separately
    facts = detect_facts(timeout=0)
    assert facts.uid == 1000
    assert facts.gid == 1000
    assert 1000 in facts.group_ids
    assert facts.running.uid == 1000
    # timeout 0 -> names fallback without calling pwd/grp successfully forced
    assert facts.user_name is None
    assert facts.groups == {}
