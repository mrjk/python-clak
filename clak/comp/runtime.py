"""General runtime flags: attended vs unattended execution.

``RuntimeOptMixin`` adds three flags describing *how the process runs*, not
what it shows, so any mixin or command can read them:

- ``--interactive WHEN``: ``auto`` (default) / ``always`` / ``never``, like
  ``ls --color=WHEN``. ``auto`` means TTY on stdin and stderr, outside CI.
- ``--no-input``: alias of ``--interactive never`` (pip, gcloud, Django).
- ``-y/--yes``: answer confirmations with yes.

Precedence for interactivity: CLI > ``$CLAK_INTERACTIVE`` > ``$CI`` > TTY.
There is deliberately no environment variable for ``--yes``.

Resolved values are published on the context as ``ctx.interactive`` and
``ctx.assume_yes`` (also ``ctx.plugins["runtime"]``), and fed to the generic
UI settings (:func:`set_ui_settings`). :func:`ui_session` only reads those
settings, so custom flags can drive ``clak.ui`` the same way.
"""

import logging
import os
import sys
from dataclasses import replace
from typing import Any, Mapping, Optional

from clak.common import to_boolean
from clak.core.descriptors import Argument
from clak.exception import ClakUserError
from clak.ui import UIAbort, UINoInputError, UIPolicy, UISession, detect_interactive

logger = logging.getLogger(__name__)

INTERACTIVE_ENV = "CLAK_INTERACTIVE"
INTERACTIVE_CHOICES = ("auto", "always", "never")


def _env_interactive(env: Mapping[str, str]) -> Optional[str]:
    """Parse ``$CLAK_INTERACTIVE`` into auto/always/never, or None."""
    raw = str(env.get(INTERACTIVE_ENV, "")).strip().lower()
    if not raw:
        return None
    if raw in INTERACTIVE_CHOICES:
        return raw
    try:
        return "always" if to_boolean(raw) else "never"
    except ValueError:
        logger.warning("Ignoring invalid %s=%r", INTERACTIVE_ENV, raw)
        return None


def resolve_runtime(
    args: Mapping[str, Any],
    env: Optional[Mapping[str, str]] = None,
    stdin=None,
    stderr=None,
) -> dict:
    """Resolve runtime flags (pure function, no side effects).

    Args:
        args: parsed CLI values (``interactive``, ``no_input``, ``yes``).
        env: environment (default ``os.environ``).
        stdin/stderr: streams used for TTY detection.

    Returns:
        ``{"interactive": bool, "assume_yes": bool, "mode": str, "source": str}``

    Raises:
        ClakUserError: ``--no-input`` combined with ``--interactive`` other than never.
    """
    env = os.environ if env is None else env
    when = args.get("interactive")
    no_input = bool(args.get("no_input"))

    if no_input and when not in (None, "never"):
        raise ClakUserError(
            "--no-input conflicts with --interactive " + str(when),
            advice="Use either --no-input or --interactive=WHEN",
        )

    source = "cli"
    if no_input:
        when = "never"
    elif when is None:
        when, source = _env_interactive(env), "env"

    if when in (None, "auto"):
        interactive = detect_interactive(stdin, stderr, env)
        source = "auto" if when is None or source == "cli" else source
        when = "auto"
    else:
        interactive = when == "always"

    return {
        "interactive": interactive,
        "assume_yes": bool(args.get("yes")),
        "mode": when,
        "source": source,
    }


class RuntimeOptMixin:  # pylint: disable=too-few-public-methods
    """``--interactive``, ``--no-input`` and ``-y/--yes`` flags."""

    yes = Argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Answer yes to confirmation prompts",
    )

    interactive = Argument(
        "--interactive",
        metavar="WHEN",
        choices=INTERACTIVE_CHOICES,
        default=None,
        help=(
            "When to prompt: auto (TTY and not CI, default), always, never "
            f"(env: {INTERACTIVE_ENV})"
        ),
    )

    no_input = Argument(
        "--no-input",
        action="store_true",
        default=False,
        help="Never prompt; use defaults or fail (same as --interactive=never)",
    )

    def cli_hook__runtime(self, instance, ctx, **_):  # pylint: disable=unused-argument
        """Resolve runtime flags and publish them on ctx."""
        values = resolve_runtime(vars(ctx.args), stdin=sys.stdin, stderr=sys.stderr)
        ctx.plugins["runtime"] = values
        ctx.interactive = values["interactive"]
        ctx.assume_yes = values["assume_yes"]
        set_ui_settings(
            ctx,
            interactive=values["interactive"],
            assume_yes=values["assume_yes"],
            hint="use --interactive=always to allow prompting",
            yes_hint="pass --yes to confirm",
        )
        logger.debug("Runtime: %s", values)


UI_SETTINGS_KEY = "ui_settings"
POLICY_KEYS = ("interactive", "assume_yes", "hint", "yes_hint", "responders")


def set_ui_settings(ctx, **values) -> dict:
    """Merge UI settings into ``ctx.plugins["ui_settings"]`` and return them.

    Any producer (``RuntimeOptMixin``, your own flags, tests) can call this.
    Policy keys: ``interactive``, ``assume_yes``, ``hint``, ``yes_hint`` and
    ``responders`` (appended, not replaced). Other keys (``stdin``,
    ``stderr``...) are passed to components as kwargs.
    """
    settings = ctx.plugins.setdefault(UI_SETTINGS_KEY, {})
    responders = values.pop("responders", None)
    if responders:
        settings["responders"] = tuple(settings.get("responders", ())) + tuple(
            responders
        )
    settings.update(values)
    return settings


def _ui_settings(ctx) -> dict:
    plugins = getattr(ctx, "plugins", None) or {}
    return dict(plugins.get(UI_SETTINGS_KEY) or {})


def ui_policy(ctx, **overrides) -> UIPolicy:
    """Build a ``clak.ui`` policy from ``ctx`` UI settings plus ``overrides``.

    Settings come from :func:`set_ui_settings` (filled by ``RuntimeOptMixin``
    or any custom flags). Without settings, interactivity is autodetected.
    Extra ``responders`` are tried before the standard ones.
    """
    settings = {**_ui_settings(ctx), **overrides}
    interactive = settings.get("interactive")
    if interactive is None:
        interactive = detect_interactive()
    policy = UIPolicy.build(
        interactive,
        bool(settings.get("assume_yes")),
        hint=settings.get("hint") or "",
        yes_hint=settings.get("yes_hint") or "",
    )
    extra = tuple(settings.get("responders") or ())
    if extra:
        policy = replace(policy, responders=extra + policy.responders)
    return policy


class ClakUISession(UISession):
    """``UISession`` whose aborts become clean CLI errors (no traceback)."""

    def _run(self, component):
        try:
            return super()._run(component)
        except UINoInputError as err:
            raise ClakUserError(
                str(err), advice="Provide the missing value or allow prompting"
            ) from err
        except UIAbort as err:
            raise ClakUserError(f"Aborted: {err}") from err


def ui_session(
    ctx, policy: Optional[UIPolicy] = None, **component_kwargs
) -> ClakUISession:
    """UI session bound to the UI settings of ``ctx``.

    ``policy`` replaces the policy built by :func:`ui_policy`. Non-policy
    settings (streams...) are used as component kwargs, updated by
    ``component_kwargs``.
    """
    settings = _ui_settings(ctx)
    kwargs = {k: v for k, v in settings.items() if k not in POLICY_KEYS}
    kwargs.update(component_kwargs)
    return ClakUISession(policy or ui_policy(ctx), **kwargs)
