# Completion

Generate shell completion scripts with argcomplete.

User guide: [Shell completion](../docs/completion.md).

## Usage

```python
from clak import CompCmdRender, Command, Parser

class App(Parser):
    completion = Command(CompCmdRender, help="Print shell completion script")
```

```bash
eval "$(python myapp.py completion --executable myapp --shell bash)"
```

::: clak.comp.completion
