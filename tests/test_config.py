"""Tests for XDG Base Directory path mixin and config loading."""

import json
import os

import pytest

from clak import Parser
from clak.comp import config as config_mod
from clak.comp.config import (
    WorkDirMixin,
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


# Work dir
# ============================


def _run(app, argv):
    args = vars(app.parse_args(argv))
    args.setdefault("__cli_self__", app)
    return app.cli_execute(args)


def _xdg_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


def _make_app(seen, *bases, meta=None):
    attrs = {"app_name": "wd"}
    attrs.update(meta or {})

    class App(*bases, Parser):
        Meta = type("Meta", (), attrs)

        def cli_run(self, ctx=None, **_):
            seen["cwd"] = os.getcwd()
            seen["work_dir"] = getattr(ctx, "work_dir", None)
            seen["config"] = dict(getattr(ctx, "config", {}) or {})
            seen["config_path"] = ctx.plugins.get("config_path")
            return None

    return App(parse=False)


def test_work_dir_flag_in_help():
    app = _make_app({}, WorkDirMixin)
    help_text = app.parser.format_help()
    assert "-W" in help_text and "--work-dir" in help_text


def test_work_dir_defaults_to_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen = {}
    _run(_make_app(seen, WorkDirMixin), [])
    assert seen["work_dir"] == str(tmp_path)
    assert seen["cwd"] == str(tmp_path)


def test_work_dir_changes_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "proj"
    target.mkdir()
    seen = {}
    _run(_make_app(seen, WorkDirMixin), ["-W", str(target)])
    assert seen["cwd"] == str(target)
    assert seen["work_dir"] == str(target)


def test_work_dir_missing_raises(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    app = _make_app({}, WorkDirMixin)
    with pytest.raises(ClakUserError, match="Work directory not found"):
        _run(app, ["--work-dir", str(tmp_path / "nope")])


@pytest.mark.parametrize(
    "bases",
    [(WorkDirMixin, XDGConfFileMixin), (XDGConfFileMixin, WorkDirMixin)],
)
def test_work_dir_local_config_found(monkeypatch, tmp_path, bases):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".wd.json").write_text(json.dumps({"src": "local"}), encoding="utf-8")
    seen = {}
    _run(_make_app(seen, *bases), ["-W", str(proj)])
    assert seen["config"] == {"src": "local"}
    assert seen["config_path"] == str(proj / ".wd.json")


def test_work_dir_falls_back_to_xdg(monkeypatch, tmp_path):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    seen = {}
    _run(_make_app(seen, WorkDirMixin, XDGConfFileMixin), ["-W", str(proj)])
    assert seen["config"] == {}
    assert seen["config_path"] == str(tmp_path / "xdg" / "wd" / "config.yaml")


def test_explicit_conf_file_beats_local(monkeypatch, tmp_path):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".wd.json").write_text(json.dumps({"src": "local"}), encoding="utf-8")
    explicit = tmp_path / "explicit.json"
    explicit.write_text(json.dumps({"src": "explicit"}), encoding="utf-8")
    seen = {}
    _run(
        _make_app(seen, WorkDirMixin, XDGConfFileMixin),
        ["--conf-file", str(explicit)],
    )
    assert seen["config"] == {"src": "explicit"}


def test_relative_conf_file_resolves_in_work_dir(monkeypatch, tmp_path):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "rel.json").write_text(json.dumps({"src": "rel"}), encoding="utf-8")
    seen = {}
    _run(
        _make_app(seen, WorkDirMixin, XDGConfFileMixin),
        ["-W", str(proj), "--conf-file", "rel.json"],
    )
    assert seen["config"] == {"src": "rel"}


def test_custom_local_names(monkeypatch, tmp_path):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".wd.json").write_text(json.dumps({"src": "dot"}), encoding="utf-8")
    (tmp_path / "wd-conf.json").write_text(
        json.dumps({"src": "custom"}), encoding="utf-8"
    )
    seen = {}
    meta = {"config_local_names": ["{app}-conf.json"]}
    _run(_make_app(seen, XDGConfFileMixin, meta=meta), [])
    assert seen["config"] == {"src": "custom"}


def test_local_lookup_disabled(monkeypatch, tmp_path):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".wd.json").write_text(json.dumps({"src": "dot"}), encoding="utf-8")
    seen = {}
    _run(_make_app(seen, XDGConfFileMixin, meta={"config_local_names": []}), [])
    assert seen["config"] == {}


def test_local_config_without_work_dir_mixin(monkeypatch, tmp_path):
    _xdg_env(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".wd.json").write_text(json.dumps({"src": "cwd"}), encoding="utf-8")
    seen = {}
    _run(_make_app(seen, XDGConfFileMixin), [])
    assert seen["config"] == {"src": "cwd"}
