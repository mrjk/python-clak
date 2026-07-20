# Views

Add a view mixin to auto-render command results and expose matching CLI options.

```python
from clak import ListViewMixin, Parser

class App(ListViewMixin, Parser):
    class Meta:
        view_cli_options = True  # or False, or ("columns", "add_index")

    def cli_run(self, **_):
        return [{"name": "ada", "role": "admin"}]
```

See the [Views guide](../docs/views.md) for usage, options, and override rules.

::: clak.comp.views
    options:
      show_source: false
      members:
        - ShowViewMixin
        - ListViewMixin
        - PprintViewMixin

::: clak.views
    options:
      show_source: false
      members:
        - ShowView
        - ListView
        - PprintView
        - ClakView
        - merge_view_settings
        - parse_columns
        - parse_sort_columns
        - format_show_payload
        - OUTPUT_FORMATS
