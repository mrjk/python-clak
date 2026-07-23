# AI primer

Paste this into an AI chat when you want accurate help writing or reviewing
**Clak** code. Prefer this file first; use the
[reference](reference.md) only for advanced topics.

!!! tip "How to use"
    Click the copy button on the block below, then paste it into your prompt
    (optionally add: “Follow this Clak context.”).

``` text title="clak-ai-primer.txt"
# Clak — AI context (primer)

Package: mrjk.clak (PyPI https://pypi.org/project/mrjk.clak/)
Import package name: clak
Python: 3.10–3.14 (requires-python >=3.10,<4.0)
Docs: https://mrjk.github.io/python-clak/

## What Clak is

Clak builds CLIs with Python classes on top of stdlib argparse.
If you know argparse, you know most of Clak. There is no Click/Typer decorator DSL.

Canonical API (prefer these names):
- Parser  — app or subcommand class (argparse.ArgumentParser)
- Argument — class attribute = one option/positional (add_argument kwargs)
- Command  — binds a child Parser as a subcommand (add_subparsers)

Aliases still work but prefer canonical names:
- ArgumentParser = Parser
- SubParser / SubCommand / Cmd = Command

## Install

pip install mrjk.clak
# optional: mrjk.clak[colors]  (coloredlogs)
# optional: mrjk.clak[config]  (PyYAML for YAML config / --format yaml)

## Minimal app

from clak import Argument, Command, Parser

class Greet(Parser):
    """Greet someone."""
    name = Argument("NAME", help="Who to greet")

    def cli_run(self, name=None, **_):
        print(f"Hello, {name}")

class App(Parser):
    """My CLI."""
    verbose = Argument("-v", "--verbose", action="store_true")
    greet = Command(Greet)

if __name__ == "__main__":
    App()  # instantiating root parses argv and runs the command

## Rules of thumb

1. Every command is a Parser subclass. Put logic in cli_run(**kwargs).
2. Argument destinations become cli_run keyword args. Use **_ for unused.
3. Parent options (on root) are visible to child cli_run.
4. Class docstring = help description. Attribute name of Command = CLI name.
5. Argument(...) uses the same kwargs as argparse add_argument().
6. Optional flags start with -/-- ; positionals are bare names (e.g. "NAME").
7. Prefer raise ClakUserError("msg") over print+sys.exit for user mistakes.
8. Mixins go LEFT of Parser: class App(LoggingOptMixin, Parser):
9. Do not invent Opt/Arg helpers — not shipped; use Argument only.
10. Do not assume env vars auto-map to CLI options — not shipped.
11. Do not use Click/Typer patterns (@app.command, typer.Option, etc.).
12. Default root App() auto-dispatches. Use App(parse=False) to build without running.

## Nested commands

class Child(Parser):
    def cli_run(self, **_):
        print("child")

class Root(Parser):
    child = Command(Child, help="Run child")

# CLI: prog child

## Errors (basic)

from clak.exception import ClakUserError

def cli_run(self, name=None, **_):
    if not name:
        raise ClakUserError("NAME is required", advice="Pass a name")

Optional Meta on root:
class Meta:
    known_exceptions = [MyAppError]  # app exceptions with .rc / .advice

## Optional components (use only when needed)

| Need | Use |
| --- | --- |
| Tables / json/csv/yaml from return value | ListViewMixin / ShowViewMixin / PprintViewMixin |
| -v logging + self.logger | LoggingOptMixin |
| XDG paths + load config file | XDGConfigMixin (--conf-file → ctx.config) |
| Emit shell completion script | CompCmdRender as a Command |

Views: return data from cli_run; mixin prints it.
Logging: configure Meta.log_levels as cumulative tiers of "LEVEL|logger".
Config: JSON always; YAML needs mrjk.clak[config]. Not merged into args.
Completion: generates argcomplete shellcode; runtime autocomplete during parse is not fully wired yet.

## Anti-patterns (do not generate)

- from clak import ListView  # wrong; use from clak.views import ListView
  Prefer mixins: from clak import ListViewMixin
- Calling .dispatch() after App() unless you used parse=False
- Hand-rolled argparse.ArgumentParser alongside Clak for the same CLI
- Claiming argument groups / mutually exclusive groups / intermixed args are built-in helpers (planned, not shipped)

## When this file is not enough

Ask for / paste the long document: “Clak AI reference” covering Meta,
hooks, views/logging/config details, testing with parse=False, and edge cases.
```
