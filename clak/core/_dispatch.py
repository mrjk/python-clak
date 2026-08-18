"""Parse, dispatch, and execute for ParserNode."""

import logging
import shlex
import sys
import traceback
from typing import Any, Dict, List, Optional, Union

from clak import exception
from clak.common import ObjectNamespace
from clak.core.argparse_ import argparse, format_argument_error
from clak.core.context import ClakContext
from clak.core.plugins import CLI_HOOK_PREFIX
from clak.runtime.facts import detect_facts
from clak.runtime.runtime import detect_runtime
from clak.runtime.settings import ClakSettings, apply_debug_logging
from clak.views import ClakView

# Same logger as parser.py so tests can patch clak.core.parser.logger
logger = logging.getLogger("clak.core.parser")


class DispatchMixin:
    """Argv parse, hook walk, and view render."""

    def parse_args(
        self, args: Optional[Union[str, List[str], Dict[str, Any]]] = None
    ) -> argparse.Namespace:
        """Parse command line arguments.

        Args:
            args: Arguments to parse, can be:
                - None: Use sys.argv[1:]
                - str: Shell-style split via ``shlex.split``
                - list: Use directly
                - dict: Return as-is

        Returns:
            Namespace: Parsed argument namespace

        Raises:
            ValueError: If args is invalid type
        """
        parser = self.parser

        if args is None:
            args = sys.argv[1:]
        elif isinstance(args, str):
            args = shlex.split(args)
        elif isinstance(args, list):
            pass
        elif isinstance(args, dict):
            return args
        else:
            raise ValueError(f"Invalid args type: {type(args)}")

        return parser.parse_args(args)

    def dispatch(  # pylint: disable=too-many-branches,too-many-statements
        self,
        args: Optional[Union[str, List[str], Dict[str, Any]]] = None,
        trace: bool = False,
        **_: Any,
    ) -> Any:
        """Main dispatch function for command execution.

        Args:
            args: Arguments to parse
            **_: Unused keyword arguments
        """

        apply_debug_logging()
        settings = ClakSettings.current()

        error = None
        try:
            args = self.parse_args(args)
            args = args.__dict__
        except argparse.ArgumentError as err:
            error = exception.ClakParseError(
                format_argument_error(err),
                parser=getattr(err, "clak_parser", None),
            )

        if not error:
            if not isinstance(args, dict):
                raise TypeError(
                    f"Parsed args must be a dict, got {type(args).__name__}"
                )

            # Check for trace mode
            if "app_trace_mode" in args:
                trace = args["app_trace_mode"]
            if settings.debug:
                trace = True

            # Leaf command (may carry Meta.cli_view / view mixins on nested cmds)
            cli_leaf = args.get("__cli_self__", self)

            # Run app command + view render (pipe breaks during print hit clean_terminate)
            try:
                data = self.cli_execute(args=args, settings=settings)

                # Prepare viewer output (CLI view mixins may stash settings on root)
                view_settings = dict(getattr(self, "_clak_view_settings", None) or {})
                ctx = getattr(self, "_clak_ctx", None)
                if ctx is not None:
                    runtime = getattr(ctx, "runtime", None)
                    if runtime is not None:
                        view_settings.setdefault("term_width", runtime.term_width)
                        view_settings.setdefault("stdout_tty", runtime.stdout_tty)
                    ctx_settings = getattr(ctx, "settings", None)
                    if ctx_settings is not None:
                        view_settings.setdefault("clak_colors", ctx_settings.colors)
                if isinstance(data, ClakView):
                    render_kwargs = ClakView.merge_settings(
                        getattr(data, "settings", None), view_settings
                    )
                    data.render(**render_kwargs)
                else:
                    viewer = cli_leaf.query_cfg_parents("cli_view", default=None)
                    if isinstance(viewer, type) and issubclass(viewer, ClakView):
                        viewer = viewer()
                    if viewer is not None:
                        if not isinstance(viewer, ClakView):
                            raise TypeError(
                                "Meta.cli_view must be a ClakView instance or subclass"
                            )
                        viewer.render(data, **view_settings)

                return data

            except Exception as err:  # pylint: disable=broad-exception-caught
                error = err

        if trace is True:
            logger.error("".join(traceback.format_exception(error)))

        # Process exception handling
        known_exceptions = self.query_cfg_parents("known_exceptions", default=[])
        self.clean_terminate(error, known_exceptions)

        # Developer catchall - unexpected bug (Paasify-style)
        if trace is False:
            logger.error("".join(traceback.format_exception(error)))
        logger.critical(
            "Uncaught error %s; this may be a bug! Please report to the developer.",
            error.__class__.__name__,
        )
        logger.critical("Error: %s", error)
        sys.exit(1)

    def cli_execute(  # pylint: disable=too-many-locals,too-many-statements
        self,
        args: Optional[Dict[str, Any]] = None,
        settings: Optional[ClakSettings] = None,
    ) -> Any:
        """Execute the command with given arguments.

        Args:
            args: Arguments to parse
            settings: Process settings (defaults to ``ClakSettings.current()``)

        Raises:
            ClakParseError: If argument parsing fails
            NotImplementedError: If command has no implementation
        """
        if not isinstance(args, dict):
            raise TypeError(
                f"cli_execute args must be a dict, got {type(args).__name__}"
            )

        hook_list = {}

        cli_command_hier = [
            value
            for key, value in sorted(args.items())
            if key.startswith("__cli_cmd__")
        ]
        args = {
            key: value
            for key, value in args.items()
            if not key.startswith("__cli_cmd__")
        }

        cli_self = self
        if "__cli_self__" in args:
            cli_self = args.pop("__cli_self__")

        fn_group_name = "cli_group"
        fn_exec_name = "cli_run"
        name = self.name
        hierarchy = cli_self.get_hierarchy()
        node_count = len(hierarchy)

        logger.debug("Run instance %s", cli_self)

        if settings is None:
            settings = ClakSettings.current()

        narrow_width = self.query_cfg_parents("runtime_narrow_width", default=None)
        ctx = ClakContext(
            registry=self.registry,
            name=name,
            app_name=self.query_cfg_parents("app_name", default=name),
            app_proc_name=self.query_cfg_parents(
                "app_proc_name", default=self.proc_name
            ),
            cli_self=cli_self,
            cli_root=self,
            cli_depth=node_count,
            cli_commands=cli_command_hier,
            args=ObjectNamespace(**args),
            runtime=detect_runtime(narrow_width=narrow_width),
            facts=detect_facts(),
            settings=settings,
        )
        self._clak_ctx = ctx  # pylint: disable=attribute-defined-outside-init

        ret = None
        for idx, node in enumerate(hierarchy):
            last_node = idx == (node_count - 1)

            logger.info("Processing node %d:%s.%s", idx, node, fn_group_name)

            node_hooks = getattr(node, "_cli_hooks", None)
            if node_hooks is None:
                node_hooks = {
                    method: getattr(node, method)
                    for method in dir(node)
                    if method.startswith(CLI_HOOK_PREFIX)
                    and callable(getattr(node, method, None))
                }
            hook_list.update(node_hooks)

            ctx.cli_parent = hierarchy[-2] if len(hierarchy) > 1 else None
            ctx.cli_parents = hierarchy[:idx]
            ctx.cli_children = dict(node.children)
            ctx.cli_last = last_node
            ctx.cli_hooks = hook_list
            ctx.cli_index = idx
            ctx.cli_state = "run_hooks"

            for hook_name, hook_fn in hook_list.items():
                logger.info("Run hook %d:%s.%s", idx, node, hook_name)
                hook_fn(node, ctx)

            ctx.cli_methods = getattr(node, "cli_methods", {})
            ctx.cli_state = "run_groups"

            group_fn = getattr(node, fn_group_name, None)
            if group_fn is not None:
                logger.info(
                    "Group function execute: %d:%s.%s", idx, node, fn_group_name
                )
                group_fn(ctx=ctx, **ctx.__dict__)

            ctx.cli_state = "run_exec"
            if last_node is True:
                run_fn = getattr(node, fn_exec_name, None)

                logger.info("Run function execute: %d:%s.%s", idx, node, fn_exec_name)
                ret = run_fn(ctx=ctx, **ctx.args.__dict__)

            ctx.cli_first = False

        return ret
