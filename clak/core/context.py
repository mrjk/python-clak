"""Typed execution context passed to hooks, ``cli_group``, and ``cli_run``."""

from typing import Any, Optional

from clak.common import ObjectNamespace


class CliArgs(ObjectNamespace):
    """Parsed CLI destinations attached as ``ctx.args``."""


class ClakContext(ObjectNamespace):
    """Per-dispatch CLI context.

    One instance is created in ``cli_execute`` and mutated as the command
    hierarchy walks (``ctx.runtime``, ``ctx.args``, ``ctx.cli_self``, ...).
    ``ctx.plugins`` holds mixin payloads and ``ctx.data`` is free scratch
    space; both are plain dicts. ``cli_group`` receives ``**ctx.as_kwargs()``.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        registry: dict,
        name: str,
        app_name: str,
        app_proc_name: Any,
        cli_self: Any,
        cli_root: Any,
        cli_depth: int,
        cli_commands: list,
        args: CliArgs,
        runtime: Any,
        settings: Any = None,
        data: Optional[dict] = None,
        plugins: Optional[dict] = None,
    ):
        super().__init__(
            registry=registry,
            name=name,
            app_name=app_name,
            app_proc_name=app_proc_name,
            cli_self=cli_self,
            cli_root=cli_root,
            cli_depth=cli_depth,
            cli_commands=cli_commands,
            args=args,
            runtime=runtime,
            settings=settings,
            data={} if data is None else dict(data),
            plugins={} if plugins is None else dict(plugins),
            cli_first=True,
            cli_state=None,
            cli_parent=None,
            cli_parents=[],
            cli_children={},
            cli_last=False,
            cli_hooks={},
            cli_index=0,
        )

    @property
    def facts(self):
        """OS/process facts (:class:`~clak.runtime.facts.FactsInfo`), built on first use."""
        facts = self.__dict__.get("facts")
        if facts is None:
            # pylint: disable-next=import-outside-toplevel
            from clak.runtime.facts import detect_facts

            facts = self.__dict__["facts"] = detect_facts()
        return facts

    @property
    def view_settings(self) -> dict:
        """Copy of view mixin settings (also in ``ctx.plugins['view_settings']``)."""
        return dict(self.plugins.get("view_settings") or {})

    @property
    def ui_settings(self) -> dict:
        """Copy of UI settings (also in ``ctx.plugins['ui_settings']``)."""
        return dict(self.plugins.get("ui_settings") or {})

    def as_kwargs(self) -> dict:
        """Context fields as a dict (same keys as ``__dict__``)."""
        return dict(self.__dict__)
