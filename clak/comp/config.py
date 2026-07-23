"""XDG Base Directory CLI path helpers.

Provides ``XDGConfigMixin`` so apps can expose standard config/data/cache/log
path flags with defaults derived from ``Meta.app_name`` and ``$XDG_*`` env vars.
"""

import argparse
import logging
import os
import re

from clak.parser import Argument

logger = logging.getLogger(__name__)

_DEFAULT_XDG = {
    "XDG_CONFIG_HOME": "~/.config",
    "XDG_DATA_HOME": "~/.local/share",
    "XDG_CACHE_HOME": "~/.cache",
}

_UNSAFE_APP_NAME = re.compile(r"[^\w.-]+")


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


# Configuration and workdir support
# ============================


class XDGConfigMixin:  # pylint: disable=too-few-public-methods
    """XDG path flags for configuration files and directories.

    Adds:
    - ``--conf-file``: ``$XDG_CONFIG_HOME/<app>/config.yaml``
    - ``--data-dir``: ``$XDG_DATA_HOME/<app>`` (hidden)
    - ``--cache-dir``: ``$XDG_CACHE_HOME/<app>`` (hidden)
    - ``--log-dir``: ``$XDG_CACHE_HOME/<app>/logs`` (hidden)

    ``<app>`` comes from ``Meta.app_name``, else the parser name / class name.
    Defaults respect ``$XDG_CONFIG_HOME``, ``$XDG_DATA_HOME``, and
    ``$XDG_CACHE_HOME`` when set.
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
