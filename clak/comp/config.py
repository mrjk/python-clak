"""XDG Base Directory path helpers and config-file loading.

Provides ``XDGConfigMixin`` so apps can expose standard config/data/cache/log
path flags with defaults from ``Meta.app_name`` / ``$XDG_*``, and load
``--conf-file`` once via ``cli_hook__config``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Mapping

from clak.common import ObjectNamespace
from clak.exception import ClakUserError
from clak.parser import Argument, MetaSetting

logger = logging.getLogger(__name__)

# Optional YAML support (extra: mrjk.clak[config])
yaml = None
try:
    import yaml  # type: ignore
except ImportError:
    pass

_DEFAULT_XDG = {
    "XDG_CONFIG_HOME": "~/.config",
    "XDG_DATA_HOME": "~/.local/share",
    "XDG_CACHE_HOME": "~/.cache",
}

_UNSAFE_APP_NAME = re.compile(r"[^\w.-]+")

_YAML_SUFFIXES = {".yaml", ".yml"}
_JSON_SUFFIXES = {".json"}
_YAML_INSTALL_HINT = "pip install 'mrjk.clak[config]'"


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


def load_config_file(path: str | Path) -> dict[str, Any]:
    """Load a mapping from a JSON or YAML config file.

    Format is detected from the file suffix (``.json``, ``.yaml``, ``.yml``).
    YAML requires the optional ``config`` extra (PyYAML).

    Raises:
        ClakUserError: Unknown suffix, missing PyYAML, I/O/parse error, or
            non-mapping root document.
    """
    conf_path = Path(path)
    suffix = conf_path.suffix.lower()

    if suffix in _JSON_SUFFIXES:
        try:
            with conf_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except OSError as err:
            raise ClakUserError(
                f"Could not read config file: {conf_path}",
                advice=str(err),
            ) from err
        except json.JSONDecodeError as err:
            raise ClakUserError(
                f"Invalid JSON in config file: {conf_path}",
                advice=str(err),
            ) from err
    elif suffix in _YAML_SUFFIXES:
        if yaml is None:
            raise ClakUserError(
                f"YAML config requires PyYAML ({conf_path})",
                advice=f"Install with: {_YAML_INSTALL_HINT}",
            )
        try:
            with conf_path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except OSError as err:
            raise ClakUserError(
                f"Could not read config file: {conf_path}",
                advice=str(err),
            ) from err
        except yaml.YAMLError as err:
            raise ClakUserError(
                f"Invalid YAML in config file: {conf_path}",
                advice=str(err),
            ) from err
    else:
        raise ClakUserError(
            f"Unsupported config format: {conf_path}",
            advice="Use a .json, .yaml, or .yml file",
        )

    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ClakUserError(
            f"Config root must be a mapping/object: {conf_path}",
            advice=f"Got {type(data).__name__}",
        )
    return dict(data)


# Configuration and workdir support
# ============================


class XDGConfigMixin:  # pylint: disable=too-few-public-methods
    """XDG path flags and config-file loading.

    Adds:
    - ``--conf-file``: ``$XDG_CONFIG_HOME/<app>/config.yaml``
    - ``--data-dir``: ``$XDG_DATA_HOME/<app>`` (hidden)
    - ``--cache-dir``: ``$XDG_CACHE_HOME/<app>`` (hidden)
    - ``--log-dir``: ``$XDG_CACHE_HOME/<app>/logs`` (hidden)

    ``<app>`` comes from ``Meta.app_name``, else the parser name / class name.
    Defaults respect ``$XDG_CONFIG_HOME``, ``$XDG_DATA_HOME``, and
    ``$XDG_CACHE_HOME`` when set.

    On dispatch, ``cli_hook__config`` loads ``--conf-file`` (JSON always;
    YAML with the ``config`` extra). Missing file yields ``{}`` unless
    ``Meta.config_required`` is true. Loaded data is available as
    ``ctx.config`` (dict) and ``cli_root.config`` (attribute namespace).
    """

    xdg_config = Argument(
        "--conf-file",
        help="Configuration file to use",
    )
    xdg_data_dir = Argument(
        "--data-dir",
        help=argparse.SUPPRESS,
    )
    xdg_cache_dir = Argument(
        "--cache-dir",
        help=argparse.SUPPRESS,
    )
    xdg_log_dir = Argument(
        "--log-dir",
        help=argparse.SUPPRESS,
    )

    meta__config__config_required = MetaSetting(
        help="If true, missing --conf-file raises ClakUserError",
    )

    _XDG_ARG_DEFAULTS = (
        ("xdg_config", "conf_file"),
        ("xdg_data_dir", "data_dir"),
        ("xdg_cache_dir", "cache_dir"),
        ("xdg_log_dir", "log_dir"),
    )

    def _xdg_app_name(self) -> str:
        """Resolve the application name used in XDG paths."""
        name = self.query_cfg_parents("app_name", default=None)
        if not name:
            name = getattr(self, "name", None) or self.__class__.__name__
        return sanitize_xdg_app_name(name)

    def add_arguments(self, arguments: dict = None):
        """Apply XDG defaults from app name / env, then register arguments."""
        arguments = dict(arguments or getattr(self, "meta__arguments_dict", {}) or {})
        paths = resolve_xdg_paths(self._xdg_app_name())

        for attr_name, path_key in self._XDG_ARG_DEFAULTS:
            template = getattr(type(self), attr_name, None)
            if not isinstance(template, Argument):
                continue
            if attr_name in arguments:
                continue
            kwargs = dict(template.kwargs)
            kwargs.setdefault("default", paths[path_key])
            arg = Argument(*template.args, **kwargs)
            arg.destination = attr_name
            arguments[attr_name] = arg

        return super().add_arguments(arguments)

    def cli_hook__config(self, instance, ctx, **_):
        """Load ``--conf-file`` once and expose it on ctx / root."""
        if ctx.cli_first:
            path = getattr(ctx.args, "xdg_config", None)
            required = bool(
                self.query_cfg_parents(
                    "config_required", default=False, include_self=True
                )
            )

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
