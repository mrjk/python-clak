# Advanced Usage

Clak provides several integrated features out of the box.

## Integrated features

* Automatic environment variable parsing
* [Error and exception handling](../docs/exceptions.md) — `ClakUserError`, exit codes, `Meta.known_exceptions`
* Automatic management of `--help` and `-h` flags

## Advanced customization

Some behavior can be overridden on a per-node or per-argument basis.

### Arguments customization

Arguments are defined directly in classes via the `Argument` class. See the
[Parser API](../api/parser.md).

### Parser `Meta`

The `Meta` class changes parser behavior. Examples:

```python
class MyApp(Parser):
    class Meta:
        app_name = "My app name"
        known_exceptions = [MyDomainError]
```

See [Error handling](../docs/exceptions.md) for exception-related `Meta` settings.
