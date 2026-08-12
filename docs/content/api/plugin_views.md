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
        - ClakViewOptMixin
        - TableViewOptMixin
        - TextLayoutOptMixin
        - TextViewOptMixin
        - ShowViewMixin
        - ListViewMixin
        - PprintViewMixin
        - RawViewMixin
        - MarkdownViewMixin
        - RstViewMixin
        - CompositeViewMixin

::: clak.views
    options:
      show_source: false
      members:
        - ShowView
        - ListView
        - PprintView
        - RawView
        - MarkdownView
        - RstView
        - CompositeView
        - ClakView
        - FeatureFullViewer
        - merge_view_settings
        - parse_columns
        - parse_sort_columns
        - parse_wrap
        - normalize_sort_columns
        - normalize_wrap
        - normalize_wrap_min
        - normalize_sections
        - format_show_payload
        - resolve_view_width
        - resolve_line_length
        - parse_line_length
        - normalize_width_mode
        - OUTPUT_FORMATS
        - TEXT_FORMATS
        - FORMAT_SCOPES
        - WIDTH_MODES
        - WRAP_MODES
        - DEFAULT_LINE_LENGTH
