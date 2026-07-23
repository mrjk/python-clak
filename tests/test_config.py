"""Tests for XDG Base Directory path mixin."""

import os

from clak.comp.config import (
    XDGConfigMixin,
    resolve_xdg_paths,
    sanitize_xdg_app_name,
    xdg_dir,
)
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
        if action.dest
        in ("xdg_config", "xdg_data_dir", "xdg_cache_dir", "xdg_log_dir")
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
    conf = next(
        a.default for a in app.parser._actions if a.dest == "xdg_config"
    )
    assert conf == str(tmp_path / "config" / "DemoTool" / "config.yaml")
