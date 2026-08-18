"""Parse, dispatch, and execute for ParserNode."""

import logging
import shlex
import sys
import traceback
from typing import Any, Dict, List, Optional, Union

from clak import exception
from clak.common import ObjectNamespace
from clak.core.argparse_ import argparse, format_argument_error
from clak.runtime.facts import detect_facts
from clak.runtime.runtime import detect_runtime
from clak.runtime.settings import CLAK_DEBUG
from clak.views import ClakView
from clak.views.base import merge_view_settings

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

    def dispatch(  # pylint: disable=too-many-branches
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
            if CLAK_DEBUG:
                trace = True

            # Leaf command (may carry Meta.cli_view / view mixins on nested cmds)
            cli_leaf = args.get("__cli_self__", self)

            # Run app command + view render (pipe breaks during print hit clean_terminate)
            try:
                data = self.cli_execute(args=args)

                # Prepare viewer output (CLI view mixins may stash settings on root)
                view_settings = getattr(self, "_clak_view_settings", None) or {}
                if isinstance(data, ClakView):
                    render_kwargs = merge_view_settings(
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
        self, args: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute the command with given arguments.

        Args:
            args: Arguments to parse

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
        fn_hook_prefix = "cli_hook__"
        name = self.name
        hierarchy = cli_self.get_hierarchy()
        node_count = len(hierarchy)

        logger.debug("Run instance %s", cli_self)

        ctx = {}
        ctx["registry"] = self.registry

        ctx["name"] = name
        ctx["app_name"] = self.query_cfg_parents("app_name", default=name)
        ctx["app_proc_name"] = self.query_cfg_parents(
            "app_proc_name", default=self.proc_name
        )

        ctx["cli_self"] = cli_self
        ctx["cli_root"] = self
        ctx["cli_depth"] = node_count
        ctx["cli_commands"] = cli_command_hier
        ctx["args"] = ObjectNamespace(**args)

        ctx["data"] = {}
        ctx["plugins"] = {}

        narrow_width = self.query_cfg_parents("runtime_narrow_width", default=None)
        ctx["runtime"] = detect_runtime(narrow_width=narrow_width)
        ctx["facts"] = detect_facts()

        ctx["cli_first"] = True
        ctx["cli_state"] = None
        ctx["cli_methods"] = None

        ret = None
        # pylint: disable=attribute-defined-outside-init
        for idx, node in enumerate(hierarchy):
            last_node = idx == (node_count - 1)

            logger.info("Processing node %d:%s.%s", idx, node, fn_group_name)

            cls_hooks = [
                method for method in dir(node) if method.startswith(fn_hook_prefix)
            ]
            for hook_name in cls_hooks:
                hook_fn = getattr(node, hook_name, None)
                if hook_fn is not None:
                    hook_list[hook_name] = hook_fn

            ctx["cli_parent"] = hierarchy[-2] if len(hierarchy) > 1 else None
            ctx["cli_parents"] = hierarchy[:idx]
            ctx["cli_children"] = dict(node.children)
            ctx["cli_last"] = last_node
            ctx["cli_hooks"] = hook_list
            ctx["cli_index"] = idx

            sorted_ctx = dict(sorted(ctx.items()))
            _ctx = ObjectNamespace(**sorted_ctx)
            _ctx.cli_state = "run_hooks"

            for hook_name, hook_fn in hook_list.items():
                logger.info("Run hook %d:%s.%s", idx, node, hook_name)
                hook_fn(node, _ctx)

            _ctx.cli_methods = getattr(node, "cli_methods", {})

            _ctx.cli_state = "run_groups"

            group_fn = getattr(node, fn_group_name, None)
            if group_fn is not None:
                logger.info(
                    "Group function execute: %d:%s.%s", idx, node, fn_group_name
                )
                group_fn(ctx=_ctx, **_ctx.__dict__)

            _ctx.cli_state = "run_exec"
            if last_node is True:
                run_fn = getattr(node, fn_exec_name, None)

                logger.info("Run function execute: %d:%s.%s", idx, node, fn_exec_name)
                ret = run_fn(ctx=_ctx, **_ctx.args.__dict__)

            ctx["cli_first"] = False

        return ret
