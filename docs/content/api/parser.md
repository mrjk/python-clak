# Module API - Parser


![Alt Text](../images/schema_parser/classes_clak.svg)

Prefer the top-level package for app code:

```python
from clak import Parser, Argument, Command
# Optional: Arg (positionals), Opt (flags) - Argument still accepts both
```

Descriptors (`Argument`, `Arg`, `Opt`, `SubParser`, docstring helpers):

::: clak.core.descriptors

Build / dispatch / execute:

::: clak.core.parser
