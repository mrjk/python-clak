# 8. Argparse wrapper and Clak-owned UI

Date: 2026-08-18

## Status

Accepted

## Context

Clak uses stdlib argparse as the parse engine (see [2. Argparse as main parser](0002-argparse-as-main-parser.md)). Parser merging is out of scope ([3. No argparse merging](0003-no-argparse-merging.md)).

Across Python 3.10-3.14, argparse APIs and messages drift: `error()` vs `ArgumentError`, intermixed re-entering `parse_known_args`, `color=` on 3.14, option-help layout on 3.13, choice quoting on 3.12. Clak also customized `--help` by subclassing private `HelpFormatter._format_*` methods and by regex-rewriting `format_help()` (empty `positional arguments:` heading, RST backticks, Rich `RegexHighlighter`).

Regex against argparse output is the wrong layer. If the stdlib string is unstable, Clak generates the string.

## Decision

Split two OOP layers. Dependency goes one way: Clak core -> `clak.core.argp` -> stdlib argparse. `argp` must not import ParserNode, descriptors, `clak.comp`, `ClakSettings`, or Rich.

1. **Adapter (`clak.core.argp`)** - stable parse API. `ArgparseCapabilities` names version quirks. `ArgumentParser` polyfills constructor kwargs, always raises `ArgumentError` when `exit_on_error=False`, guards intermixed reentrancy, and emits quoted invalid-choice lists. `ErrorRenderer` formats parse errors from `ArgumentError` objects.

2. **Help UI (`HelpRenderer` on ParserNode)** - structured `HelpDocument` from ParserNode, Argument, and Command. No `HelpFormatter` regex, no Rich highlighter on argparse text. Rich color (in `clak.comp.help`) styles document parts. `Meta.help_formatter = RecursiveHelpFormatter` remains the public opt-out of color.

Hard rule: do not parse, patch, or restyle `format_help()`, `format_usage()`, or `ArgumentError` text with regex.

Python 3.10-3.11 stdlib intermixed still slices the first 7 characters of `format_usage()`. Usage stays an uncolored `usage:` prefix. That is an adapter constraint, not a reason to keep argparse as the help engine.

## Consequences

Help and errors are Clak-stable across 3.10-3.14. Private argparse access shrinks to parsing. Parser merging is not supported (see ADR 0003); the old inject path was removed. Public `Parser` / `Argument` / `Command` names stay the same.
