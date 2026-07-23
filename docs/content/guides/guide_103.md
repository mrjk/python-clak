# Customization

Clak ships sensible defaults. This guide covers what you commonly tweak next:
`Meta`, help text, and built-in behaviour.

## Built-in behaviour (no mixin)

These work on any `Parser`:

* Automatic `--help` / `-h`
* Instantiating the root parser parses argv and runs the matched command
  (pass `parse=False` to build without dispatching)
* [Error and exception handling](../docs/exceptions.md) —
  `ClakUserError`, exit codes, `Meta.known_exceptions`

Clak does **not** auto-map arbitrary environment variables to CLI options.
Library flags that *do* read the environment:

* `CLAK_DEBUG`, `CLAK_COLORS` — see [Logging](../docs/logging.md)
* `$XDG_*` — see [Config](../docs/config.md) when using `XDGConfigMixin`

Env-var → option mapping is on the [roadmap](../project/roadmap.md).

## Arguments

Define arguments on the class with `Argument` — same kwargs as
`argparse.ArgumentParser.add_argument()`. See the
[Parser API](../api/parser.md).

```python
class MyCmd(Parser):
    verbose = Argument("-v", "--verbose", action="store_true", help="Verbose")
    path = Argument("PATH", help="Input path")
```

## Parser `Meta`

Nested `Meta` changes parser behaviour. Common settings:

```python
class MyApp(Parser):
    class Meta:
        app_name = "myapp"              # XDG paths, process naming
        help_description = "My CLI"     # override docstring-based description
        known_exceptions = [MyDomainError]
```

Exception-related settings: [Error handling](../docs/exceptions.md).
Logging / views / config each document their own `Meta` keys on their guides.

## Inheritance

Share options or helpers via a base class:

```python
class BaseCmd(Parser):
    dry_run = Argument("--dry-run", action="store_true")

    def maybe_write(self, dry_run=False, **_):
        if dry_run:
            print("skip write")
            return
        ...

class ApplyCmd(BaseCmd):
    def cli_run(self, **kwargs):
        self.maybe_write(**kwargs)
```

Parent options are visible to child `cli_run` methods when using nested
`Command`s — see [Nested commands](guide_102.md).

## Next steps

* Components: [guide 104](guide_104.md) (views, logging, config, completion)
* Deeper nesting patterns: [Advanced](../docs/advanced.md)
* Shipping an entry point: [Shipping your CLI](../docs/execution.md)
