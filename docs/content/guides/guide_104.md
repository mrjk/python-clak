# Applications components

Components are pluggable features for your parser classes. They can provide
arguments and participate in the parser tree lifecycle. See also the
[logging](../api/plugin_logging.md) and [views](../api/plugin_views.md) API pages.


## Views component

Render command results as tables (or pretty-prints) with a single mixin.
Full walkthrough: [Views](../docs/views.md).

``` python title="script_views.py" linenums="1"
--8<-- "examples/script_views.py"
```


## Logging component

This component provides logging features to your application:

``` python title="script5.py" linenums="1"
--8<-- "examples/script5.py"
```

## Completion component

TODO

## Config component

TODO
