"""Tests for XDG Base Directory path mixin and config loading."""

import json
import os

import pytest

from clak import Parser
from clak.comp import config as config_mod
from clak.comp.config import (
    XDGCacheDirMixin,
    XDGConfFileMixin,
    XDGDataDirMixin,
    XDGLogDirMixin,
    load_config_file,
    resolve_xdg_paths,
    sanitize_xdg_app_name,
    xdg_dir,
)
from clak.exception import ClakUserError

pytestmark = pytest.mark.tags("unit-tests")


def test_sanitize_xdg_app_name():
    assert sanitize_xdg_app_name("my_app") == "my_app"
    assert sanitize_xdg_app_name("My App") == "My_App"
    assert sanitize_xdg_app_name("  ") == "app"
    assert sanitize_xdg_app_name("a/b") == "a_b"


def test_xdg_dir_uses_env_then_default(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert xdg_dir("XDG_CONFIG_HOME") == os.path.expanduser("~/.config")

    custom = str(tmp_path / "cfg")
    monkeypatch.setenv("XDG_CONFIG_HOME", custom)
    assert xdg_dir("XDG_CONFIG_HOME") == custom


def test_resolve_xdg_paths_respects_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    paths = resolve_xdg_paths("demo")
    assert paths["conf_file"] == str(tmp_path / "config" / "demo" / "config.yaml")
    assert paths["data_dir"] == str(tmp_path / "data" / "demo")
    assert paths["cache_dir"] == str(tmp_path / "cache" / "demo")
    assert paths["log_dir"] == str(tmp_path / "cache" / "demo" / "logs")


def _option_dests(app):
    return {a.dest: a.default for a in app.parser._actions}


def test_xdg_mixins_defaults_use_meta_app_name(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    class App(
        XDGConfFileMixin, XDGDataDirMixin, XDGCacheDirMixin, XDGLogDirMixin, Parser
    ):
        class Meta:
            app_name = "cool-cli"

        def cli_run(self, **_):
            return None

    defaults = _option_dests(App(parse=False))
    assert defaults["conf_file"] == str(
        tmp_path / "config" / "cool-cli" / "config.yaml"
    )
    assert defaults["data_dir"] == str(tmp_path / "data" / "cool-cli")
    assert defaults["cache_dir"] == str(tmp_path / "cache" / "cool-cli")
    assert defaults["log_dir"] == str(tmp_path / "cache" / "cool-cli" / "logs")


def test_conf_file_mixin_alone_adds_only_conf_file():
    class App(XDGConfFileMixin, Parser):
        def cli_run(self, **_):
            return None

    dests = _option_dests(App(parse=False))
    assert "conf_file" in dests
    for name in ("data_dir", "cache_dir", "log_dir"):
        assert name not in dests


def test_data_dir_mixin_alone_has_no_conf_file(tmp_path):
    seen = {}

    class App(XDGDataDirMixin, Parser):
        class Meta:
            app_name = "data-only"

        def cli_run(self, ctx=None, **_):
            seen["config"] = getattr(ctx, "config", None)
            return None

    app = App(parse=False)
    dests = _option_dests(app)
    assert "data_dir" in dests
    assert "conf_file" not in dests
    assert "--data-dir" in app.parser.format_help()
    app.cli_execute({"data_dir": str(tmp_path), "__cli_self__": app})
    assert seen["config"] is None


def test_conf_file_mixin_falls_back_to_class_name(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    class DemoTool(XDGConfFileMixin, Parser):
        def cli_run(self, **_):
            return None

    app = DemoTool(parse=False)
    conf = next(a.default for a in app.parser._actions if a.dest == "conf_file")
    assert conf == str(tmp_path / "config" / "DemoTool" / "config.yaml")


def test_load_config_file_json(tmp_path):
    path = tmp_path / "app.json"
    path.write_text(json.dumps({"debug": True, "name": "x"}), encoding="utf-8")
    assert load_config_file(path) == {"debug": True, "name": "x"}


def test_load_config_file_json_null_root(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("null", encoding="utf-8")
    assert load_config_file(path) == {}


def test_load_config_file_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ClakUserError, match="Invalid JSON"):
        load_config_file(path)


def test_load_config_file_non_dict_root(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ClakUserError, match="mapping"):
        load_config_file(path)


def test_load_config_file_unknown_suffix(tmp_path):
    path = tmp_path / "app.toml"
    path.write_text("x = 1", encoding="utf-8")
    with pytest.raises(ClakUserError, match="Unsupported config format"):
        load_config_file(path)


def test_load_config_file_yaml_missing_pyyaml(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "_yaml", None)
    path = tmp_path / "app.yaml"
    path.write_text("debug: true\n", encoding="utf-8")
    with pytest.raises(ClakUserError, match="PyYAML") as exc:
        load_config_file(path)
    assert "mrjk.clak[config]" in (exc.value.advice or "")


@pytest.mark.skipif(config_mod._yaml is None, reason="PyYAML not installed")
def test_load_config_file_yaml(tmp_path):
    path = tmp_path / "app.yaml"
    path.write_text("debug: true\nname: demo\n", encoding="utf-8")
    assert load_config_file(path) == {"debug": True, "name": "demo"}


def test_hook_missing_file_yields_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    seen = {}

    class App(XDGConfFileMixin, Parser):
        class Meta:
            app_name = "hook-demo"

        def cli_run(self, ctx=None, **_):
            seen["config"] = dict(ctx.config)
            seen["root"] = getattr(self, "config", None)
            return seen["config"]

    app = App(parse=False)
    missing = tmp_path / "config" / "hook-demo" / "config.yaml"
    assert not missing.exists()
    result = app.cli_execute({"conf_file": str(missing), "__cli_self__": app})
    assert result == {}
    assert seen["config"] == {}
    assert seen["root"] is not None


def test_hook_loads_json(tmp_path):
    conf = tmp_path / "settings.json"
    conf.write_text(json.dumps({"port": 8080}), encoding="utf-8")
    seen = {}

    class App(XDGConfFileMixin, Parser):
        def cli_run(self, ctx=None, **_):
            seen["config"] = dict(ctx.config)
            seen["port"] = self.config.port
            seen["path"] = ctx.plugins["config_path"]
            return seen["config"]

    app = App(parse=False)
    result = app.cli_execute({"conf_file": str(conf), "__cli_self__": app})
    assert result == {"port": 8080}
    assert seen["port"] == 8080
    assert seen["path"] == str(conf)


def test_hook_config_required_missing_file(tmp_path):
    class App(XDGConfFileMixin, Parser):
        class Meta:
            config_required = True

        def cli_run(self, **_):
            return None

    app = App(parse=False)
    missing = tmp_path / "nope.json"
    with pytest.raises(ClakUserError, match="not found"):
        app.cli_execute({"conf_file": str(missing), "__cli_self__": app})
