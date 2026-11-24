"""Bind ``clak.ui`` prompts to a dispatch context.

Producers (``RuntimeOptMixin``, your own flags, tests) store settings with
:func:`set_ui_settings`; consumers call :func:`ui_session` (or
:func:`ui_policy`) from ``cli_run``.
"""

from dataclasses import replace
from typing import Optional

from clak.exception import ClakUserError
from clak.ui import UIAbort, UINoInputError, UIPolicy, UISession, detect_interactive

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
