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
    ArgumentParser, SubParser, SubCommand, Cmd,  # aliases
    LoggingOptMixin,
    ShowViewMixin, ListViewMixin, PprintViewMixin,
    RawViewMixin, MarkdownViewMixin, RstViewMixin, CompositeViewMixin,
    XDGConfigMixin,
    CompCmdRender, CompRenderCmdMixin, CompRenderOptMixin,
    OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, SUPPRESS,  # argparse constants
)
from clak.exception import (
    ClakError, ClakUserError, ClakParseError, ClakExitError,
    ClakAppError, ClakNotImplementedError, ClakBugError,
)
from clak.views import ListView, ShowView, PprintView, RawView, MarkdownView, RstView, CompositeView, ClakView  # not re-exported at clak top-level

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
PprintViewMixin — pprint; --width
RawViewMixin — plain text; --width
MarkdownViewMixin — markdown text; --format view|raw, --width
RstViewMixin — reStructuredText; --format view|raw, --width
CompositeViewMixin — return CompositeView(...); table flags + --format-scope first|all

Flags (list/show): --columns, --add-index/--no-add-index,
  --expand-keys/--no-expand-keys (list),
  --format view|yaml|json|csv, --sort-columns, --sort-mode,
  --width min|auto|terminal (default terminal; no wrap when non-TTY),
  --wrap last|all (tables only; default last; only when fitting to terminal)
Flags (markdown/rst): --format view|raw (view=rendered, raw=source), --width
Flags (composite): table flags + --format-scope first|all (machine export)
Meta.view_width sets the default width mode.
Meta.view_wrap sets the default table wrap mode.
Meta.view_format_scope sets CompositeView machine export scope.
yaml format needs PyYAML (mrjk.clak[config] or pip install pyyaml).
Markdown render needs rich (pip install rich); RST render needs docutils
(pip install docutils). --format raw needs no extra package.

Without a mixin / returned ClakView / Meta.cli_view, return values are not printed.

Manual view:
  from clak.views import ListView
  return ListView(rows, columns=["name"])

CLI flags override options set on a returned view (may log a warning).

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
HELP GROUPS (shipped)
==============================================================================

Argument(..., group="Title") places the flag under a titled --help section.
Same title reuses one group. View mixins use group="Output options".

==============================================================================
NOT SHIPPED (do not invent APIs)
==============================================================================

- Opt / Arg split helpers
- Automatic env-var → option mapping (beyond CLAK_* and XDG_*)
- Mutually exclusive argument groups
- Intermixed optional/positional helpers
- Decorator-first Click/Typer style primary API
- from clak import ListView  (use clak.views or mixins)

==============================================================================
QUICK CHECKLIST FOR GENERATED CODE
==============================================================================

[ ] Imports from clak use Parser, Argument, Command (+ mixins as needed)
[ ] Mixin(s) appear before Parser in class bases
[ ] cli_run uses destinations + **_ ; raises ClakUserError / AppError for UX
[ ] Root instantiated under if __name__ == "__main__" or entry point
[ ] Views: return data; do not print tables by hand if mixin present
[ ] Config: read ctx.config; do not expect magic merge into kwargs
[ ] No fictional Clak APIs; when unsure, use plain argparse kwargs on Argument
```
