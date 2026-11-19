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
``ctx.assume_yes`` (also ``ctx.plugins["runtime"]``). ``clak.ui`` can consume
them through :func:`ui_policy` / :func:`ui_session`, but nothing requires it.
"""

import logging
import os
import sys
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
        logger.debug("Runtime: %s", values)


def ui_policy(ctx) -> UIPolicy:
    """Build a ``clak.ui`` policy from the runtime values on ``ctx``.

    Without ``RuntimeOptMixin`` this falls back to autodetection.
    """
    values = ctx.plugins.get("runtime") or {}
    interactive = values.get("interactive")
    if interactive is None:
        interactive = detect_interactive()
    return UIPolicy.build(
        interactive,
        bool(values.get("assume_yes")),
        hint="use --interactive=always to allow prompting",
        yes_hint="pass --yes to confirm",
    )


class ClakUISession(UISession):
    """``UISession`` whose aborts become clean CLI errors (no traceback)."""

    def _run(self, component):
        try:
            return super()._run(component)
        except UINoInputError as err:
            raise ClakUserError(str(err), advice="Run unattended with defaults or --yes") from err
        except UIAbort as err:
            raise ClakUserError(f"Aborted: {err}") from err


def ui_session(ctx, **component_kwargs) -> ClakUISession:
    """UI session bound to the runtime policy of ``ctx``."""
    return ClakUISession(ui_policy(ctx), **component_kwargs)
