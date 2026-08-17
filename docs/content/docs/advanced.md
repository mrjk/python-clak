# Nested commands


## Advanced Features and Best Practices

### 1. Command Inheritance

You can create a base command class to share functionality:

```python
class BaseCommand(Parser):
    def common_method(self):
        pass

class SpecificCommand(BaseCommand):
    def cli_run(self):
        self.common_method()
```

### 2. Argument Inheritance

Ancestor flags are copied onto descendant parsers by default
(`propagate=True`). Opt out per flag with `propagate=False`. `cli_run` on a
leaf still receives parent dests, and the flags may appear before or after
the subcommand name. See
[Ancestor flags on descendants](#propagate-options).

```python
class AppMain(Parser):
    verbose = Argument("--verbose", action="store_true")
    
    class SubCommand(Parser):
        def cli_run(self, verbose=False, **_):
            if verbose:
                print("Verbose mode enabled")
```

For structured `-v` / `-vv` logging tiers, prefer `LoggingOptMixin`
(see [Logging](logging.md)) instead of a hand-rolled boolean flag.
A mixin is optional when the flag already sits on a parent parser.

### 3. Named help groups and exclusive groups {#named-help-groups-and-exclusive-groups}

Clak-only kwargs on `Argument` (stripped before `add_argument`):

| Key | Role |
| --- | --- |
| `option_group="Title"` | Help section (typical for options) |
| `argument_group="Title"` | Help section (typical for positionals) |
| `exclusive_group="key"` | At most one member may be set (argparse mutual exclusion) |
| `propagate=False` | Do not copy this flag onto descendant parsers |

`option_group` and `argument_group` are the same feature under two names: the same
title string reuses one `add_argument_group`. Do not set both on one Argument.
`exclusive_group` enforces XOR at parse time (`required=False`); it does not
create a titled help section by itself, but may nest under a help group when
both are set.

```python
from clak import Argument, Parser

class App(Parser):
    catalog = Argument("--catalog", help="Pick a catalog")
    format = Argument(
        "--format",
        choices=["view", "json"],
        option_group="Output options",
        help="Output format",
    )
    columns = Argument(
        "--columns",
        option_group="Output options",
        help="Columns to show",
    )
    json = Argument("--json", action="store_true", exclusive_group="fmt")
    yaml = Argument("--yaml", action="store_true", exclusive_group="fmt")

    def cli_run(self, **_):
        return None
```

`App(parse=False, add_help=True).parser.format_help()` shows `--catalog` under
the default options section and `--format` / `--columns` under
**Output options**. Passing both `--json` and `--yaml` is a parse error.

Subcommand grouping is formatter metadata (not a second `add_subparsers`).
`Meta.command_groups` is ordered `(key, title)` pairs on that Parser only.
`Command(..., command_group="key")` is stripped before `add_parser`. Keys
without members are omitted. Commands with no `command_group` stay under
leftover `subcommands:`. Ungrouped CLIs keep a single `subcommands:` list.

`--help` lists nested children by default (`Meta.help_subcommands = "all"`).
Set `"top"` on the root (inherited; a child may override) for immediate
children only. Nested names hide the parent path by default
(`Meta.help_hide_parent = True`); set `False` for flattened paths such as
`tool leaf`. Grouping and listing depth are independent.

```python
from clak import Command, Parser

class ToolGroup(Parser):
    def cli_run(self, **_):
        return None

class RenderCmd(Parser):
    def cli_run(self, **_):
        return None

class OrphanCmd(Parser):
    def cli_run(self, **_):
        return None

class App(Parser):
    class Meta:
        command_groups = (
            ("base", "subcommands (base):"),
            ("dynamic", "subcommands (dynamic):"),
        )

    tool = Command(ToolGroup, command_group="base")
    render = Command(RenderCmd, command_group="dynamic")
    orphan = Command(OrphanCmd)
```

### Intermixed flags and positionals {#parse-intermixed}

The command path is ordered (`app grep`). Once a command is selected, that
command's own flags and positionals may mix. This is **on by default**.
Set `Meta.parse_intermixed = False` to get argparse leftover errors after a
flag.

The difference shows up with `nargs="*"` or `nargs="+"` (and a fixed
`nargs=N` greater than 1). A single required positional is unchanged:
`cmd file --force` already works either way. Unknown flags (`--nope`) still
error either way. Extra tokens for a single positional (`NAME` then a spare
word) still error either way.

```python
from clak import Arg, Command, Opt, Parser

class Grep(Parser):
    pattern = Arg("pattern")
    files = Arg("files", nargs="*")
    ignore_case = Opt("-i", "--ignore-case", action="store_true")

    def cli_run(self, pattern, files, ignore_case=False, **_):
        return None

class App(Parser):
    grep = Command(Grep, help="Search files")
```

CLI: `app grep foo a.txt -i b.txt`

| `parse_intermixed` | Result |
| --- | --- |
| `True` (default) | `pattern=foo`, `ignore_case=True`, `files=['a.txt', 'b.txt']` |
| `False` | error: `unrecognized arguments: b.txt` |

These are equivalent when the default is on:

```text
app grep foo a.txt -i b.txt
app grep -i foo a.txt b.txt
app grep foo -i a.txt b.txt
```

Opt out on a node (inherited; a child may set `True` again):

```python
class App(Parser):
    class Meta:
        parse_intermixed = False
```

Parent flags are copied onto descendants by default (see
[Ancestor flags on descendants](#propagate-options)). Nodes with
subcommands keep standard parse for themselves (argparse cannot intermix
`add_subparsers`). `nargs="..."` remainder is incompatible and falls back to
standard parse. Do not mix a flag and a positional in one `exclusive_group`
when using intermixed parse.

### Ancestor flags on descendants {#propagate-options}

Ancestor **flags** (not positionals) are copied onto descendant parsers at
build time. Default on. Both placements work without redeclaring the option
on the leaf:

```text
app --verbose grep foo
app grep --verbose foo
```

```python
verbose = Opt("--verbose", action="store_true")  # propagates
quiet = Opt("--quiet", action="store_true", propagate=False)  # opt out
```

Opt out with `propagate=False`. Argparse's own `-h` / `--help` is not a
Clak Argument, so it is not copied.

Copies use `default=argparse.SUPPRESS` so a value set on the parent is not
reset when the leaf does not see the flag. Leaf `--help` lists them in a
dedicated `parent options:` section (rename with
`Meta.propagate_options_group`). Closer ancestor wins when the same dest or
option strings appear on more than one node. The same command class under
two roots only inherits flags from that instance's parent chain.

Disable all copying on a node (inherited; a child may set `True` again):

```python
class App(Parser):
    class Meta:
        propagate_options = False
```

Required parent flags still must appear **before** the subcommand (argparse
validates them on the parent first). Exclusive groups do not span parse
stages. Mixin/class inheritance still shares flags across unrelated
commands; this feature is the command tree.

### 4. Custom Help Messages

Override the default help behavior:

```python
def cli_run(self, **_):
    print("Custom usage information:")
    self.show_usage()
    print("\nDetailed help:")
    self.show_help()
```

For colored `--help`, see [Colored help](help.md). Opt out with
`Meta.help_formatter = RecursiveHelpFormatter`.

### 5. Command Organization Best Practices

1. **Logical Grouping**:
   - Group related commands under common parents
   - Use meaningful command names
   - Keep the hierarchy shallow (3-4 levels max)

2. **Argument Design**:
   - Put shared options in parent commands
   - Use consistent naming across commands
   - Provide sensible defaults

3. **Documentation**:
   - Write clear help messages
   - Document command relationships
   - Include examples in docstrings

4. **Code Structure**:
   - One class per command
   - Use inheritance for shared behavior
   - Keep command implementations focused

## Error Handling and Validation

For production CLI apps, prefer Clak's built-in exception pipeline instead of
manual `print` + `return 1`. See [Error handling](exceptions.md) for patterns
used in Paasify (domain translation, `result.error` guards, `Meta.known_exceptions`).

```python
from clak.exception import ClakUserError

def cli_run(self, name=None, **_):
    if not name:
        raise ClakUserError("NAME is required")
```

## Testing Nested Commands

1. **Test Command Structure**:

```python
def test_command_structure():
    app = AppMain()
    assert hasattr(app, 'command1')
    assert hasattr(app.command1, 'sub1')
```

2. **Test Command Execution**:

```python
def test_command_execution():
    app = AppMain()
    result = app.dispatch(['command1', 'John'])
    assert result == 0
```
