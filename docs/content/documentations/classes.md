# Core classes

A Clak app is a tree of `Parser` classes. Each class is one command: it declares
its arguments and subcommands as class attributes and implements what runs.
Clak builds the argparse parsers from those declarations, parses `sys.argv`,
then walks the command path and calls your code.

All public names are importable from `clak`:

``` python
from clak import Parser, Command, Argument, Arg, Opt
```

## Overview

| Class | Kind | Role |
| --- | --- | --- |
| `Parser` | command class | Base class for every command (root and subcommands). Instantiating the root parses `sys.argv` and runs. |
| `ParserNode` | command class | Base of `Parser` without auto-dispatch. Rarely used directly. |
| `Argument` | descriptor | A positional argument or a flag. Takes the same arguments as `argparse.add_argument()`. |
| `Arg` | descriptor | `Argument` restricted to positionals (`Arg("NAME")`). |
| `Opt` | descriptor | `Argument` restricted to flags (`Opt("--force", "-f")`). |
| `Command` | descriptor | Attaches a `Parser` subclass as a subcommand. Alias of `SubParser`. |
| `ClakContext` | runtime object | Passed as `ctx` to hooks, `cli_group` and `cli_run`. |
| `ClakView` | output | Base of the views that render `cli_run` return values. See [Views](views.md). |

Legacy aliases are still exported: `ArgumentParser` (= `Parser`), `SubParser`,
`SubCommand` and `Cmd` (= `Command`). Prefer the canonical names.

``` mermaid
classDiagram
    direction LR
    class ParserNode {
        cli_group(ctx)
        cli_run(ctx, **args)
        dispatch()
    }
    class Parser
    class Argument
    class Arg
    class Opt
    class Command {
        cls
    }
    ParserNode <|-- Parser
    Argument <|-- Arg
    Argument <|-- Opt
    Parser o-- Argument : class attributes
    Parser o-- Command : class attributes
    Command --> Parser : instantiates
```

## A complete example

``` python title="users.py" linenums="1"
from clak import Arg, Command, ListViewMixin, Opt, Parser


class UserList(ListViewMixin, Parser):  # (1)!
    """List users."""

    class Meta:  # (2)!
        view_columns = ("name", "role")

    def cli_run(self, **_):
        return [{"name": "ada", "role": "admin", "city": "London"}]  # (3)!


class UserAdd(Parser):
    """Add a user."""

    name = Arg("NAME", help="User name")  # (4)!
    admin = Opt("--admin", action="store_true", help="Grant admin")

    def cli_run(self, name, admin=False, dry_run=False, **_):  # (5)!
        print(f"add {name} admin={admin} dry_run={dry_run}")


class Users(Parser):
    """Manage users."""

    ls = Command(UserList, help="List users")  # (6)!
    add = Command(UserAdd, help="Add a user")


class App(Parser):
    """Demo app."""

    class Meta:
        app_name = "demo"

    dry_run = Opt("--dry-run", action="store_true", help="Do not change anything")
    users = Command(Users, help="Manage users")


if __name__ == "__main__":
    App()  # (7)!
```

1. A view mixin renders the return value of `cli_run`. See [Plugins](plugins.md).
2. `Meta` holds class-level settings. Here, the default columns of the table.
3. Return data instead of printing it; the view formats it.
4. The class attribute name (`name`) is the argparse destination.
5. Parsed values arrive as keyword arguments. Flags of parent commands
   (`--dry-run`) are available too. Always keep `**_` for the rest.
6. The attribute name (`ls`) is the subcommand name on the command line.
7. Instantiating the root parses `sys.argv` and runs the selected command.

``` raw
$ python users.py users ls
+------+-------+
| name | role  |
+------+-------+
| ada  | admin |
+------+-------+

$ python users.py users add bob --admin --dry-run
add bob admin=True dry_run=True
```

## `Parser`

Subclass `Parser` for every command, the root included. The class docstring is
the help description; its first line is the short help shown in the parent's
subcommand list.

Methods you implement:

| Method | Called | Purpose |
| --- | --- | --- |
| `cli_run(self, ctx, **args)` | Once, on the last command of the path | The command implementation. Its return value is rendered by the view, if any. |
| `cli_group(self, ctx, **ctx_fields)` | On every command of the path, root first | Shared setup for a command group (open a client, check a precondition...). |

If a command with subcommands is called alone, the default `cli_run` prints its
help. A leaf command without `cli_run` raises `ClakNotImplementedError`.

Useful methods you call:

| Method | Purpose |
| --- | --- |
| `self.show_help()` / `self.show_usage()` | Print the help or usage of this command. |
| `self.cli_exit(status=0, message=None)` | Exit with a status code. |
| `self.cli_exit_error(message)` | Abort with a usage error. |
| `self.ctx` | The `ClakContext` of the current run (None before dispatch). |
| `self.children`, `self["name"]` | Child command instances. |

### Running the root

``` python
App()                       # parse sys.argv and run (default)
app = App(parse=False)      # build only
app.dispatch(["users", "ls"])  # parse and run an explicit argv
```

`parse=False` is useful in tests and when embedding the CLI in another program.
Only the root dispatches; subcommand instances are created by `Command`.

### `Meta` settings

Configuration lives in a nested `Meta` class (or in `meta__<name>` class
attributes). Most settings are looked up on the command, then on its parents,
so a value set on the root applies to the whole tree unless a child overrides
it.

| Setting | Purpose |
| --- | --- |
| `name` | Parser name (defaults to the class name). |
| `app_name` | Application name, used for XDG paths and `ctx.app_name`. |
| `app_proc_name` | Program name shown in usage (defaults to `argv[0]`). |
| `help_usage`, `help_description`, `help_epilog` | Override help texts. The description defaults to the docstring. |
| `help_formatter` | argparse `HelpFormatter` class. Set `RecursiveHelpFormatter` to disable colors. |
| `help_subcommands` | `"all"` (nested commands, default) or `"top"` (direct children only). |
| `help_hide_parent` | Hide the parent path in nested command lists (default `True`). |
| `command_groups` | Ordered `(key, title)` pairs to split subcommands into help sections. |
| `parse_intermixed` | Mix flags and positionals freely (default `True`). |
| `abbrev_commands` | Accept a unique prefix of a subcommand name (default `False`). See [Abbreviations](advanced.md#abbreviations). |
| `abbrev_options` | Accept a unique prefix of a long flag (default `True`). |
| `propagate_options` | Copy ancestor flags onto this command (default `True`). |
| `propagate_options_group` | Help section title for those copied flags (default `parent options`). |
| `known_exceptions`, `exception_handlers` | Extra exceptions turned into clean errors. See [Error handling](exceptions.md). |
| `cli_view` | View class or instance that renders `cli_run` return values. |
| `runtime_narrow_width` | Column threshold for `ctx.runtime.is_narrow` (default 80). |

Mixins add their own settings (`log_prefix`, `view_columns`, `config_required`...).
They are listed on the [Plugins](plugins.md) page.

## `Argument`, `Arg` and `Opt`

Declare arguments as class attributes. The attribute name is the destination,
so the value arrives in `cli_run` under that name.

``` python
class Deploy(Parser):
    target = Arg("TARGET", help="Where to deploy")              # positional
    force = Opt("--force", "-f", action="store_true")           # flag
    tags = Argument("--tag", action="append", default=[])       # either form
    level = Opt()                                               # --level, from the attribute name
```

All `argparse.add_argument()` keywords work (`action`, `nargs`, `choices`,
`type`, `default`, `metavar`, `required`, `help`...). Clak adds a few:

| Keyword | Purpose |
| --- | --- |
| `option_group` / `argument_group` | Put the argument in a titled help section. Same title, same section. |
| `exclusive_group` | Arguments sharing the same key are mutually exclusive. |
| `propagate` | `False` keeps a flag on this command only; by default flags are copied to descendants. |

`Arg` rejects names starting with `-`, `Opt` requires them. Use `Argument` when
you do not care.

### Flag propagation

A flag declared on a parent is also accepted after a subcommand:
`app --dry-run users add bob` and `app users add bob --dry-run` are equivalent.
Copied flags are listed under `parent options` in the child help. A child can
redefine a flag with the same destination to override it. Disable propagation
per flag with `propagate=False`, or per command with `Meta.propagate_options = False`.

## `Command`

`Command(cls, **kwargs)` attaches a `Parser` subclass as a subcommand. The
attribute name is the command name. Keyword arguments go to argparse
`add_parser()` (`help`, `aliases`...), plus `command_group` to place the command
in a section declared by the parent's `Meta.command_groups`.

``` python
class App(Parser):
    class Meta:
        command_groups = (("main", "Main commands"), ("misc", "Other"))

    users = Command(Users, help="Manage users", command_group="main")
    version = Command(Version, help="Show version", command_group="misc")
```

Subcommands can also be given as a dict in `meta__subcommands_dict`, and
arguments in `meta__arguments_dict`, when they are built dynamically.

## The execution context (`ctx`)

On each run, Clak creates one `ClakContext` and walks the command path from the
root to the selected command. For each command it runs:

1. the `cli_hook__*` methods collected so far (see [Plugins](plugins.md)),
2. `cli_group()`,
3. `cli_run()`, on the last command only.

``` mermaid
sequenceDiagram
    participant D as Dispatcher
    participant R as App (root)
    participant U as Users
    participant L as UserList (leaf)
    D->>R: hooks, cli_group
    D->>U: hooks, cli_group
    D->>L: hooks, cli_group, cli_run
    L-->>D: return value
    D->>D: render with view
```

Main `ctx` fields:

| Field | Content |
| --- | --- |
| `ctx.args` | All parsed values (namespace). |
| `ctx.cli_self` | The selected (leaf) command instance. |
| `ctx.cli_root` | The root instance. |
| `ctx.cli_parent`, `ctx.cli_parents`, `ctx.cli_children` | Navigation around the current node. |
| `ctx.cli_first`, `ctx.cli_last`, `ctx.cli_index`, `ctx.cli_depth` | Position in the walk. `cli_first` is handy for one-time work in hooks. |
| `ctx.app_name`, `ctx.app_proc_name` | Application names. |
| `ctx.runtime` | Terminal facts: width, TTY, `is_narrow`... |
| `ctx.facts` | Host facts (OS, CI...). |
| `ctx.settings` | Process settings from `CLAK_*` environment variables. |
| `ctx.plugins` | Dict filled by mixins (`config`, `runtime`, `view_settings`...). |
| `ctx.data` | Free dict to share state between `cli_group` and `cli_run`. |

Mixins also publish shortcuts such as `ctx.config`, `ctx.work_dir`,
`ctx.interactive` and `ctx.assume_yes`.

## Returning output

Prefer returning data from `cli_run` over printing it. When the command has a
view (via a view mixin or `Meta.cli_view`), Clak renders the return value and
applies the output flags (`--format`, `--columns`...). A `ClakView` instance
returned directly is rendered too. Without a view, the return value is not
printed. See [Views](views.md) and [Plugins](plugins.md#views).
