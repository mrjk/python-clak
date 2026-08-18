"""Typed execution context passed to hooks, ``cli_group``, and ``cli_run``."""

from typing import Any, Optional

from clak.common import ObjectNamespace


class ClakContext(ObjectNamespace):
    """Per-dispatch CLI context.

    One instance is created in ``cli_execute`` and mutated as the command
    hierarchy walks. Attribute access matches the old dict/namespace bag
    (``ctx.runtime``, ``ctx.args``, ``ctx.cli_self``, ...). ``cli_group``
    still receives ``**ctx.__dict__``.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-locals,useless-parent-delegation
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
        args: ObjectNamespace,
        runtime: Any,
        facts: Any,
        settings: Any = None,
        data: Optional[dict] = None,
        plugins: Optional[dict] = None,
        cli_first: bool = True,
        cli_state: Optional[str] = None,
        cli_methods: Any = None,
        cli_parent: Any = None,
        cli_parents: Optional[list] = None,
        cli_children: Optional[dict] = None,
        cli_last: bool = False,
        cli_hooks: Optional[dict] = None,
        cli_index: int = 0,
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
            facts=facts,
            settings=settings,
            data={} if data is None else data,
            plugins={} if plugins is None else plugins,
            cli_first=cli_first,
            cli_state=cli_state,
            cli_methods=cli_methods,
            cli_parent=cli_parent,
            cli_parents=[] if cli_parents is None else cli_parents,
            cli_children={} if cli_children is None else cli_children,
            cli_last=cli_last,
            cli_hooks={} if cli_hooks is None else cli_hooks,
            cli_index=cli_index,
        )

    def as_kwargs(self) -> dict:
        """Context fields as a dict (same keys as ``__dict__``)."""
        return dict(self.__dict__)
