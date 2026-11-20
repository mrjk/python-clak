"""JSON / YAML / CSV text serialization shared by every view.

JSON / YAML helpers return text without a trailing newline; CSV keeps the
line endings written by :mod:`csv`.
"""

from __future__ import annotations

import csv
import io
import json

from clak._optional import require

STRUCTURED_FORMATS = frozenset({"json", "yaml"})


def require_yaml():
    """Import PyYAML or raise ClakUserError with the config extra hint."""
    return require("yaml", "YAML output")


def dump_json(obj, *, compact: bool = False) -> str:
    """JSON text; unknown objects are stringified."""
    return json.dumps(obj, indent=None if compact else 2, default=str)


def dump_yaml(obj, *, anchors: bool = True, yaml=None, **kwargs) -> str:
    """Block-style YAML text in insertion order (safe dumper).

    ``anchors=False`` expands shared references instead of emitting
    ``&anchor`` / ``*alias``. Extra *kwargs* go to ``yaml.dump``.
    """
    yaml = yaml or require_yaml()
    dumper = yaml.SafeDumper
    if not anchors:

        # pylint: disable-next=too-many-ancestors,too-few-public-methods
        class _NoAliasDumper(yaml.SafeDumper):
            def ignore_aliases(self, _data):
                """Always expand shared references."""
                return True

        dumper = _NoAliasDumper
    text = yaml.dump(
        obj, Dumper=dumper, sort_keys=False, default_flow_style=False, **kwargs
    )
    return text.rstrip("\n")


def dump(obj, fmt: str, **kwargs) -> str:
    """Serialize *obj* as ``json`` or ``yaml``."""
    if fmt == "json":
        return dump_json(obj, **kwargs)
    if fmt == "yaml":
        return dump_yaml(obj, **kwargs)
    raise ValueError(
        f"Unsupported format {fmt!r}, choose one of: {sorted(STRUCTURED_FORMATS)}"
    )


def dump_csv(rows, headers) -> str:
    """CSV text with a header row (``\\r\\n`` line endings, as csv writes)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()
