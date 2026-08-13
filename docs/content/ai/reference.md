# AI reference

Technical context for AI assistants when the
[primer](primer.md) is not enough (Meta, mixins, hooks, testing, edge cases).

!!! tip "How to use"
    Click the copy button on the block below and paste into your prompt.
    You can paste the [primer](primer.md) first, then this file.

``` text title="clak-ai-reference.txt"
# Clak — AI context (reference)

Companion to the Clak AI primer. Package: mrjk.clak; import: clak.
Python 3.10–3.14. Site: https://mrjk.github.io/python-clak/

Assume the primer rules still apply (Parser / Argument / Command,
App() auto-dispatch, mixin-left-of-Parser, no Click/Typer DSL).

==============================================================================
PUBLIC SURFACE
==============================================================================

from clak import (
    Parser, Argument, Command,          # core
    Arg, Opt,                           # optional: positionals vs flags
    ArgumentParser, SubParser, SubCommand, Cmd,  # aliases
    LoggingOptMixin, RichHelpMixin,
    ShowViewMixin, ListViewMixin, PprintViewMixin, DataViewMixin,
    RawViewMixin, MarkdownViewMixin, RstViewMixin, CompositeViewMixin,
    XDGConfigMixin,
    CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin,
    OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, SUPPRESS, RecursiveHelpFormatter,
)
from clak.exception import (
    ClakError, ClakUserError, ClakParseError, ClakExitError,
    ClakAppError, ClakNotImplementedError, ClakBugError,
)
from clak.views import ListView, ShowView, PprintView, DataView, RawView, MarkdownView, RstView, CompositeView, ClakView  # not re-exported at clak top-level

# Package layout (implementation): clak.core, clak.runtime, clak.views, clak.comp.
# Prefer top-level ``from clak import ...``. Old deep paths (clak.parser, clak.nodes,
# clak.table_formatter, …) remain import-compatible via re-exports.

ParserNode is the implementation base; users subclass Parser.

==============================================================================
LIFECYCLE
==============================================================================

- Root Parser.__init__ builds the argparse tree, then calls dispatch() unless
  parse=False.
- dispatch() parses argv (or given args), walks the command chain, runs
  cli_hook__* hooks, then cli_run on the matched node, wrapped in try/except
  → clean_terminate() for known errors.
- Leaf without cli_run → ClakNotImplementedError.
- Non-leaf default cli_run shows help if children exist.

Testing / libraries:
  app = App(parse=False)
  app.dispatch(["greet", "Ada"])   # or list of argv tokens

cli_run signature: keyword args for destinations + often ctx, and **_.
Parent destinations are included when nested.

On ctx (attached once at execute start):
  ctx.runtime  - core TTY/launch/display/size (eager, local)
  ctx.facts    - optional OS sugar (lazy host/user/distro)
  See docs: Runtime and facts. Meta.runtime_narrow_width configures is_narrow.
  CLAK_FACTS_TIMEOUT default 30s for blocking fact resolves (-1 = none).

Useful helpers on self:
  self.show_help() / show_usage()
  self.cli_exit(status, message=None)
  self.cli_exit_error(message)   # argparse-style error

Prefer ClakUserError over cli_exit_error for app-level user mistakes so the
handler chain can format advice + rc consistently.

==============================================================================
ARGUMENT & COMMAND DETAILS
==============================================================================

class MyCmd(Parser):
    force = Argument("--force", "-f", action="store_true", help="Force")
    items = Argument("-m", "--items", action="append")
    color = Argument("--color", choices=["red", "green"])
    name = Argument("NAME")                    # required positional
    surname = Argument("SURNAME", nargs="?", default="Doe")
    aliases = Argument("ALIAS", nargs="*")

# Same kwargs as argparse.ArgumentParser.add_argument
# Destination defaults to the Python attribute name (force, items, ...).

Binding subcommands:
  child = Command(ChildParser, help="...")
# Optional kwargs may be passed through to subparser setup; keep help clear.
# Attribute name == CLI token (child → `prog child`).

Inheritance: subclass a base Parser to share Arguments and helper methods.
Deep trees: Command pointing at a Parser that itself has Command children.

==============================================================================
META
==============================================================================

Nested class Meta configures the node (and often inherits via parent query):

class App(Parser):
    class Meta:
        app_name = "myapp"                 # XDG paths, identity
        app_proc_name = "myapp"            # process name if needed
        help_usage = "..."
        help_description = "..."           # else class docstring
        help_epilog = "..."
        help_formatter = RecursiveHelpFormatter  # opt out of colored --help
        help_subcommands = "all"           # default; "top" for immediate children
        help_hide_parent = True            # False: show "tool netmap" paths
        command_groups = (("base", "subcommands (base):"),)
        known_exceptions = [AppError]      # list of exception types
        exception_handlers = [...]         # third-party handlers
        cli_view = ListView                # without mixin flags
        runtime_narrow_width = 80          # ctx.runtime.is_narrow threshold

Logging Meta (with LoggingOptMixin):
        log_prefix = __name__
        log_suffix = None | "==FLAT==" | "==NESTED==" | SUPPRESS | ".suffix"
        log_default_level = "WARNING"
        log_levels = [                     # cumulative -v tiers
            ["WARNING|myapp"],             # no -v
            ["INFO|myapp"],                # -v
            ["DEBUG|myapp"],               # -vv
            ["DEBUG|"],                    # -vvv empty name = root logger
        ]
        log_silent = ["urllib3"]           # WARNING until max verbosity

Views Meta (with view mixins):
        view_cli_options = True | False | ("columns", "format", ...)
        view_sort_columns = ("name",) | "name,-1" | [-1, 1]
        view_sort_mode = "asc" | "desc"

Config Meta (with XDGConfigMixin):
        app_name = "myapp"
        config_required = False            # True → missing file is error

==============================================================================
ERROR HANDLING
==============================================================================

Handler order in clean_terminate roughly:
1. Meta.known_exceptions (your AppError tree with .rc / .advice)
2. Meta.exception_handlers (third-party)
3. Built-in Clak* errors
4. Some OS errors (FileNotFoundError, PermissionError, ...)
   BrokenPipeError from | head / | tail: quiet exit 1 (no traceback / Exception ignored)
5. Else: traceback + “report to developer”, exit 1

Typical app pattern:

class AppError(Exception):
    rc = 1
    advice = None
    def __init__(self, message, rc=None, advice=None):
        if rc is not None: self.rc = rc
        self.advice = advice
        super().__init__(message)

class App(Parser):
    class Meta:
        known_exceptions = [AppError]

Env: CLAK_DEBUG=1 enables early library debug / trace-like behaviour.
CLI: --trace (from LoggingOptMixin) shows traceback before handlers.

Do not wrap every cli_run in try/except unless translating third-party errors
into AppError.

==============================================================================
VIEWS
==============================================================================

Pick ONE mixin (MRO: mixin before Parser):

class App(ListViewMixin, Parser):
    def cli_run(self, **_):
        return [{"name": "ada", "role": "admin"}]   # auto table

ShowViewMixin  — one record
ListViewMixin  — many rows
PprintViewMixin — pprint; --line-length
DataViewMixin — JSON/YAML dump; --format json|yaml (auto: yaml if PyYAML else json),
                --compact/--no-compact, --color/--no-color, --anchors/--no-anchors
RawViewMixin — plain text; --line-length
MarkdownViewMixin — markdown text; --format view|raw, --line-length
RstViewMixin — reStructuredText; --format view|raw, --line-length
CompositeViewMixin — return CompositeView(...); table flags + --line-length + --format-scope first|all

Flags (list/show): --columns, --add-index/--no-add-index,
  --expand-keys/--no-expand-keys (list),
  --format view|yaml|json|csv, --sort-columns, --sort-mode,
  --width content|fit|terminal (default terminal; no wrap when non-TTY),
  --wrap last|first|all|COL,... (tables only; default last; flexible columns
  expand or shrink to the terminal; ignored when width is content or non-TTY)
Flags (markdown/rst/raw/pprint): --line-length N|terminal|nowrap (default 120)
Flags (markdown/rst): --format view|raw (view=rendered, raw=source)
Flags (composite): table flags + --line-length + --format-scope first|all
Meta.view_width sets the default table width mode.
Meta.view_line_length sets the default text wrap (int, terminal, or nowrap).
Meta.view_wrap names the flexible table columns (last, first, all, or column list).
Meta.view_wrap_min sets shrink floors for those columns (positive int or column-spec map).
Meta.view_format_scope sets CompositeView machine export scope.
yaml format needs PyYAML (mrjk.clak[config] or pip install pyyaml).
Markdown render needs mrjk.clak[markdown] (rich); RST render needs
mrjk.clak[rst] (docutils). --format raw needs no extra package.
Composite --format is table-scoped (view|yaml|json|csv); markdown source is
in --format-scope all envelopes. Optional section meta:
  (name, view, {title, description}) -> human === Title === plus
  description (Rich markup when backend allows; === chrome dimmed);
  envelope fields only when set. Hide --expand-keys with
  view_cli_options when the composite primary is ShowView.

Without a mixin / returned ClakView / Meta.cli_view, return values are not printed.

Manual view:
  from clak.views import ListView
  return ListView(rows, columns=["name"])

CLI flags override options set on a returned view (may log a warning).

==============================================================================
RICH HELP
==============================================================================

Colored --help is the Parser default when Rich is installed and stdout is a
TTY. No mixin required.

class App(Parser):
    class Meta:
        help_description = "Hello [bold]World[/bold]"  # markup when color on
        help_epilog = "..."

No CLI flags. Needs mrjk.clak[markdown] (rich). Color: TTY stdout, NO_COLOR,
CLAK_COLORS, CLAK_COLOR_BACKEND. Missing rich / none / NO_COLOR / non-TTY =
plain RecursiveHelpFormatter layout. Opt out:
    class Meta:
        help_formatter = RecursiveHelpFormatter  # from clak
RichHelpMixin is optional (re-opt-in a child after a parent opt-out).
Argument help= stays literal. CompositeView title/description use the same
markup helper.

==============================================================================
LOGGING
==============================================================================

class App(LoggingOptMixin, Parser):
    class Meta:
        log_prefix = "myapp"
        log_levels = [["INFO|myapp"], ["DEBUG|myapp"]]

    def cli_run(self, **_):
        self.logger.info("hi")
        self.logger.success("ok")   # custom levels: spam, verbose, success, notice

Flags: -v/--verbose (count), --log-format default|extended|audit|debug,
       --trace/--no-trace, --log-colors/--no-log-colors (always present).

Ownership: either Clak manages logging (use mixin) OR the app owns logging
(omit mixin; do not mix both for the same process).

--log-colors default: CLAK_LOG_COLORS if set, else on when CLAK_COLORS and
stderr is a TTY. ANSI formatting needs coloredlogs (mrjk.clak[colors]).
CLAK_COLORS=0 is a hard kill-switch for coloredlogs / Clak color integration.

==============================================================================
CONFIG (XDG)
==============================================================================

class App(XDGConfigMixin, Parser):
    class Meta:
        app_name = "cool-cli"

    def cli_run(self, ctx, **_):
        data = ctx.config          # dict
        # also root.config as attribute namespace

Flags: --conf-file (visible); --data-dir / --cache-dir / --log-dir (hidden).
Defaults under $XDG_CONFIG_HOME/<app>/config.yaml etc.
JSON always; YAML needs mrjk.clak[config].
Missing file → {} unless config_required=True.
Config is NOT merged into argparse destinations — read ctx.config explicitly.

==============================================================================
COMPLETION
==============================================================================

from clak import CompCmdRender, Command, Parser

class App(Parser):
    completion = Command(CompCmdRender, help="Print shell completion script")

# eval "$(prog completion --executable prog --shell bash)"
# shells: bash zsh tcsh fish powershell

CompRenderOptMixin adds --completion flag instead of a subcommand.
Shipped capability = emit argcomplete shellcode. Runtime
argcomplete.autocomplete() during parse is still planned / incomplete —
do not document it as fully working unless the codebase clearly enables it.

==============================================================================
HOOKS & PLUGINS (advanced)
==============================================================================

Components participate via methods named cli_hook__<name> on the parser /
mixin. They run during dispatch before cli_run. Prefer existing mixins over
inventing hooks unless extending Clak itself.

Build reusable mixins the same way: class attributes with Argument, Meta
settings (meta__config__*), and optional cli_hook__* / cli_run overrides.
Always put mixins before Parser in the bases list.

==============================================================================
SHIPPING
==============================================================================

Entry point should construct the root Parser:

def main():
    App()

# pyproject.toml
# [project.scripts]
# myapp = "mypkg.cli:main"

==============================================================================
HELP GROUPS AND EXCLUSIVE GROUPS (shipped)
==============================================================================

Argument(..., option_group="Title") or argument_group="Title" places the flag
under a titled --help section. Same title reuses one section (do not set both
kwargs on one Argument). View mixins use option_group="Output options".

Argument(..., exclusive_group="key") maps to add_mutually_exclusive_group
(at most one member; required=False). May combine with a help-group kwarg.

Command(..., command_group="key") plus Meta.command_groups = ((key, title), ...)
splits --help subcommand lists. Formatter metadata only (stash on argparse
choice actions); not a second add_subparsers. Ungrouped CLIs keep one
subcommands: list. Leftover commands with no command_group stay under
subcommands:. Per-command (does not inherit to children). Do not set
Meta.help_formatter to group commands.

Meta.help_subcommands = "all" (default) lists nested commands.
"top" lists immediate children only. Meta.help_hide_parent = True (default)
shows the leaf name indented two spaces per depth (not tool netmap). Set
False for flattened paths. Inherited; a child may override. Independent of
command_groups. Do not set Meta.help_formatter to change listing layout.

Breaking: the old group= kwarg was removed; use option_group= / argument_group=.

==============================================================================
OPTIONAL ARG / OPT HELPERS
==============================================================================

Argument still accepts both positionals and flags. Arg and Opt are optional
sugar (not aliases of Argument):

- Arg("NAME", help="...")  # positional only; Arg("--flag") raises ValueError
- Opt("-v", "--verbose")   # flags only; Opt("NAME") raises ValueError

Same kwargs as Argument / add_argument(). Mixing kinds in one call also
raises. Prefer Argument in generated code unless the user asked for Arg/Opt.

==============================================================================
NOT SHIPPED (do not invent APIs)
==============================================================================

- Automatic env-var → option mapping (beyond CLAK_* and XDG_*)
- Intermixed optional/positional helpers
- Decorator-first Click/Typer style primary API
- from clak import ListView  (use clak.views or mixins)

==============================================================================
QUICK CHECKLIST FOR GENERATED CODE
==============================================================================

[ ] Imports from clak use Parser, Argument, Command (+ mixins as needed)
[ ] Arg/Opt only if requested; do not mix positional names with -/-- flags
[ ] Mixin(s) appear before Parser in class bases
[ ] cli_run uses destinations + **_ ; raises ClakUserError / AppError for UX
[ ] Root instantiated under if __name__ == "__main__" or entry point
[ ] Views: return data; do not print tables by hand if mixin present
[ ] Config: read ctx.config; do not expect magic merge into kwargs
[ ] No fictional Clak APIs; when unsure, use plain argparse kwargs on Argument
```
