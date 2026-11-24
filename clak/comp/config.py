"""XDG Base Directory path helpers and config-file loading.

Each XDG path flag is its own opt-in mixin, with defaults from
``Meta.app_name`` / ``$XDG_*``:

- ``XDGConfFileMixin``: ``--conf-file``, loaded once via ``cli_hook__config``
- ``XDGDataDirMixin``: ``--data-dir``
- ``XDGCacheDirMixin``: ``--cache-dir``
- ``XDGLogDirMixin``: ``--log-dir``

Plus ``WorkDirMixin`` (``-W/--work-dir``), which changes the process working
directory. ``XDGConfFileMixin`` looks up a project-local config file in the
work directory before falling back to the XDG default.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Mapping

from clak._optional import require
from clak.common import ObjectNamespace
from clak.core.descriptors import Argument, MetaSetting
from clak.exception import ClakUserError

logger = logging.getLogger(__name__)

_DEFAULT_XDG = {
    "XDG_CONFIG_HOME": "~/.config",
    "XDG_DATA_HOME": "~/.local/share",
    "XDG_CACHE_HOME": "~/.cache",
}

_UNSAFE_APP_NAME = re.compile(r"[^\w.-]+")

_DEFAULT_LOCAL_NAMES = (".{app}.yaml", ".{app}.yml", ".{app}.json")


def xdg_dir(env_var: str, default: str | None = None) -> str:
    """Resolve an XDG base directory from the environment.

    Uses ``$env_var`` when set and non-empty; otherwise expands ``default``
    (or the XDG Base Directory default for that variable).
    """
    value = os.environ.get(env_var)
    if value:
        return value
    if default is None:
        default = _DEFAULT_XDG[env_var]
    return os.path.expanduser(default)


def sanitize_xdg_app_name(name: str) -> str:
    """Turn an app name into a safe path segment under XDG directories."""
    cleaned = _UNSAFE_APP_NAME.sub("_", str(name).strip()).strip("._-")
    return cleaned or "app"


def resolve_xdg_paths(app_name: str) -> dict[str, str]:
    """Build conf/data/cache/log paths for ``app_name`` under XDG bases."""
    safe_name = sanitize_xdg_app_name(app_name)
    config_home = xdg_dir("XDG_CONFIG_HOME")
    data_home = xdg_dir("XDG_DATA_HOME")
    cache_home = xdg_dir("XDG_CACHE_HOME")
    return {
        "conf_file": os.path.join(config_home, safe_name, "config.yaml"),
        "data_dir": os.path.join(data_home, safe_name),
        "cache_dir": os.path.join(cache_home, safe_name),
        "log_dir": os.path.join(cache_home, safe_name, "logs"),
    }


def _json_loader():
    return json.load, json.JSONDecodeError


def _yaml_loader():
    yaml = require("yaml", "YAML config")
    return yaml.safe_load, yaml.YAMLError


# suffix -> (label, () -> (load function, parse error class))
_CONFIG_LOADERS = {
    ".json": ("JSON", _json_loader),
    ".yaml": ("YAML", _yaml_loader),
    ".yml": ("YAML", _yaml_loader),
}


def load_config_file(path: str | Path) -> dict[str, Any]:
    """Load a mapping from a JSON or YAML config file.

    Format is detected from the file suffix (``.json``, ``.yaml``, ``.yml``).
    YAML requires the optional ``config`` extra (PyYAML).

    Raises:
        ClakUserError: Unknown suffix, missing PyYAML, I/O/parse error, or
            non-mapping root document.
    """
    conf_path = Path(path)
    entry = _CONFIG_LOADERS.get(conf_path.suffix.lower())
    if entry is None:
        raise ClakUserError(
            f"Unsupported config format: {conf_path}",
            advice="Use a .json, .yaml, or .yml file",
        )
    label, get_loader = entry
    load, parse_error = get_loader()
    try:
        with conf_path.open(encoding="utf-8") as handle:
            data = load(handle)
    except OSError as err:
        raise ClakUserError(
            f"Could not read config file: {conf_path}", advice=str(err)
        ) from err
    except parse_error as err:
        raise ClakUserError(
            f"Invalid {label} in config file: {conf_path}", advice=str(err)
        ) from err

    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ClakUserError(
            f"Config root must be a mapping/object: {conf_path}",
            advice=f"Got {type(data).__name__}",
        )
    return dict(data)


def resolve_work_dir(ctx) -> Path:
    """Resolve (and apply once) the work directory for this dispatch.

    Idempotent: the first call reads ``ctx.args.work_dir``; when set, it
    changes the process cwd to it. The result is cached in
    ``ctx.plugins["work_dir"]``. Without ``--work-dir``, the inherited cwd is
    the work directory. Any hook may call this, whatever the hook order.

    Raises:
        ClakUserError: ``--work-dir`` is not an existing directory.
    """
    cached = ctx.plugins.get("work_dir")
    if cached is not None:
        return Path(cached)

    raw = getattr(ctx.args, "work_dir", None)
    if raw:
        target = Path(os.path.expanduser(str(raw)))
        if not target.is_dir():
            raise ClakUserError(
                f"Work directory not found: {target}",
                advice="Pass an existing directory to --work-dir",
            )
        os.chdir(target)
        logger.debug("Changed working directory to %s", target)

    work_dir = Path.cwd()
    ctx.plugins["work_dir"] = str(work_dir)
    return work_dir


class WorkDirMixin:  # pylint: disable=too-few-public-methods
    """``-W/--work-dir`` flag: run as if started in another directory.

    Defaults to the current directory inherited from the parent process.
    The resolved path is available as ``ctx.work_dir`` and
    ``ctx.plugins["work_dir"]``.
    """

    work_dir = Argument(
        "-W",
        "--work-dir",
        help="Run as if started in this directory (default: current directory)",
    )

    def cli_hook__work_dir(self, instance, ctx, **_):  # pylint: disable=unused-argument
        """Apply ``--work-dir`` once and expose it on ctx."""
        ctx.work_dir = str(resolve_work_dir(ctx))


# XDG path mixins (one per flag, opt-in)
# ============================


# Flag attributes whose default comes from ``resolve_xdg_paths()`` (same key).
_XDG_PATH_FLAGS = frozenset({"conf_file", "data_dir", "cache_dir", "log_dir"})


class _XDGPathMixin:  # pylint: disable=too-few-public-methods
    """Shared helpers for XDG path mixins.

    Each subclass declares one ``Argument`` named after a
    ``resolve_xdg_paths`` key; its default is injected by ``_prepare_argument``.
    """

    def _xdg_app_name(self) -> str:
        """Resolve the application name used in XDG paths."""
        name = self.query_cfg_parents("app_name", default=None)
        if not name:
            name = getattr(self, "name", None) or self.__class__.__name__
        return sanitize_xdg_app_name(name)

    def _prepare_argument(self, key: str, arg: Argument) -> Argument:
        """Inject the XDG default path for this mixin's flag."""
        arg = super()._prepare_argument(key, arg)
        if key in _XDG_PATH_FLAGS and "default" not in arg.kwargs:
            arg = arg.with_kwargs(default=resolve_xdg_paths(self._xdg_app_name())[key])
        return arg


class XDGConfFileMixin(_XDGPathMixin):  # pylint: disable=too-few-public-methods
    """``--conf-file`` flag and config-file loading.

    Default: ``$XDG_CONFIG_HOME/<app>/config.yaml``, where ``<app>`` comes
    from ``Meta.app_name``, else the parser name / class name.

    Lookup order (first match wins, one file is loaded):

    1. explicit ``--conf-file`` (relative paths resolve against the work dir)
    2. first existing file from ``Meta.config_local_names`` in the work dir
       (default ``.<app>.yaml``, ``.<app>.yml``, ``.<app>.json``; ``{app}``
       is substituted; ``[]`` disables the local lookup)
    3. the XDG default above

    The work dir is ``--work-dir`` when ``WorkDirMixin`` is used, else the cwd.

    On dispatch, ``cli_hook__config`` loads ``--conf-file`` (JSON always;
    YAML with the ``config`` extra). Missing file yields ``{}`` unless
    ``Meta.config_required`` is true. Loaded data is available as
    ``ctx.config`` (dict) and ``cli_root.config`` (attribute namespace).
    """

    conf_file = Argument(
        "--conf-file",
        help="Configuration file to use",
    )

    meta__config__config_required = MetaSetting(
        help="If true, missing --conf-file raises ClakUserError",
    )

    meta__config__config_local_names = MetaSetting(
        help=(
            "Config file names looked up in the work dir before the XDG "
            "default ('{app}' is replaced by the app name; [] disables)"
        ),
    )

    def _find_local_config(self, work_dir: Path) -> Path | None:
        """Return the first existing local config candidate in ``work_dir``."""
        names = self.query_cfg_parents("config_local_names", default=None)
        if names is None:
            names = _DEFAULT_LOCAL_NAMES
        app = self._xdg_app_name()
        for name in names:
            candidate = work_dir / str(name).format(app=app)
            if candidate.is_file():
                return candidate
        return None

    def cli_hook__config(self, instance, ctx, **_):
        """Load ``--conf-file`` once and expose it on ctx / root."""
        if ctx.cli_first:
            work_dir = resolve_work_dir(ctx)
            path = getattr(ctx.args, "conf_file", None)
            xdg_default = resolve_xdg_paths(self._xdg_app_name())["conf_file"]
            if not path or str(path) == xdg_default:
                local = self._find_local_config(work_dir)
                if local is not None:
                    logger.debug("Using work-dir config: %s", local)
                    path = str(local)
            required = bool(self.query_cfg_parents("config_required", default=False))

            if not path:
                data: dict[str, Any] = {}
                if required:
                    raise ClakUserError(
                        "Configuration file path is required",
                        advice="Pass --conf-file PATH",
                    )
            else:
                conf_path = Path(path)
                if not conf_path.is_file():
                    if required:
                        raise ClakUserError(
                            f"Configuration file not found: {conf_path}",
                            advice="Create the file or pass --conf-file PATH",
                        )
                    logger.debug(
                        "Config file missing, using empty config: %s", conf_path
                    )
                    data = {}
                else:
                    data = load_config_file(conf_path)

            ctx.plugins["config"] = data
            ctx.plugins["config_path"] = str(path) if path else None
            ctx.cli_root.config = ObjectNamespace(**data)
            logger.debug(
                "Config loaded for %s from %s (%d keys)",
                instance,
                path,
                len(data),
            )

        # Re-attach each hierarchy step (fresh ObjectNamespace per node)
        ctx.config = ctx.plugins.get("config", {})


class XDGDataDirMixin(_XDGPathMixin):  # pylint: disable=too-few-public-methods
    """``--data-dir`` flag, default ``$XDG_DATA_HOME/<app>``."""

    data_dir = Argument(
        "--data-dir",
        help="Data directory",
    )


class XDGCacheDirMixin(_XDGPathMixin):  # pylint: disable=too-few-public-methods
    """``--cache-dir`` flag, default ``$XDG_CACHE_HOME/<app>``."""

    cache_dir = Argument(
        "--cache-dir",
        help="Cache directory",
    )


class XDGLogDirMixin(_XDGPathMixin):  # pylint: disable=too-few-public-methods
    """``--log-dir`` flag, default ``$XDG_CACHE_HOME/<app>/logs``."""

    log_dir = Argument(
        "--log-dir",
        help="Log directory",
    )
