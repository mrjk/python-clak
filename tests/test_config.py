"""Tests for XDG Base Directory path mixin and config loading."""

import json
import os

import pytest

from clak.comp import config as config_mod
from clak.comp.config import (
    XDGConfigMixin,
    load_config_file,
    resolve_xdg_paths,
    sanitize_xdg_app_name,
    xdg_dir,
)
from clak.exception import ClakUserError
from clak.parser import Parser


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


def test_xdg_config_mixin_defaults_use_meta_app_name(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    class App(XDGConfigMixin, Parser):
        class Meta:
            app_name = "cool-cli"

        def cli_run(self, **_):
            return None

    app = App(parse=False)
    defaults = {
        action.dest: action.default
        for action in app.parser._actions
        if action.dest in ("xdg_config", "xdg_data_dir", "xdg_cache_dir", "xdg_log_dir")
    }
    assert defaults["xdg_config"] == str(
        tmp_path / "config" / "cool-cli" / "config.yaml"
    )
    assert defaults["xdg_data_dir"] == str(tmp_path / "data" / "cool-cli")
    assert defaults["xdg_cache_dir"] == str(tmp_path / "cache" / "cool-cli")
    assert defaults["xdg_log_dir"] == str(tmp_path / "cache" / "cool-cli" / "logs")


def test_xdg_config_mixin_falls_back_to_class_name(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    class DemoTool(XDGConfigMixin, Parser):
        def cli_run(self, **_):
            return None

    app = DemoTool(parse=False)
    conf = next(a.default for a in app.parser._actions if a.dest == "xdg_config")
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
    monkeypatch.setattr(config_mod, "yaml", None)
    path = tmp_path / "app.yaml"
    path.write_text("debug: true\n", encoding="utf-8")
    with pytest.raises(ClakUserError, match="PyYAML") as exc:
        load_config_file(path)
    assert "mrjk.clak[config]" in (exc.value.advice or "")


@pytest.mark.skipif(config_mod.yaml is None, reason="PyYAML not installed")
def test_load_config_file_yaml(tmp_path):
    path = tmp_path / "app.yaml"
    path.write_text("debug: true\nname: demo\n", encoding="utf-8")
    assert load_config_file(path) == {"debug": True, "name": "demo"}


def test_hook_missing_file_yields_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    seen = {}

    class App(XDGConfigMixin, Parser):
        class Meta:
            app_name = "hook-demo"

        def cli_run(self, ctx=None, **_):
            seen["config"] = dict(ctx.config)
            seen["root"] = getattr(self, "config", None)
            return seen["config"]

    app = App(parse=False)
    missing = tmp_path / "config" / "hook-demo" / "config.yaml"
    assert not missing.exists()
    result = app.cli_execute({"xdg_config": str(missing), "__cli_self__": app})
    assert result == {}
    assert seen["config"] == {}
    assert seen["root"] is not None


def test_hook_loads_json(tmp_path):
    conf = tmp_path / "settings.json"
    conf.write_text(json.dumps({"port": 8080}), encoding="utf-8")
    seen = {}

    class App(XDGConfigMixin, Parser):
        def cli_run(self, ctx=None, **_):
            seen["config"] = dict(ctx.config)
            seen["port"] = self.config.port
            seen["path"] = ctx.plugins["config_path"]
            return seen["config"]

    app = App(parse=False)
    result = app.cli_execute({"xdg_config": str(conf), "__cli_self__": app})
    assert result == {"port": 8080}
    assert seen["port"] == 8080
    assert seen["path"] == str(conf)


def test_hook_config_required_missing_file(tmp_path):
    class App(XDGConfigMixin, Parser):
        class Meta:
            config_required = True

        def cli_run(self, **_):
            return None

    app = App(parse=False)
    missing = tmp_path / "nope.json"
    with pytest.raises(ClakUserError, match="not found"):
        app.cli_execute({"xdg_config": str(missing), "__cli_self__": app})
