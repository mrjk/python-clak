# Clak

Class-based command-line interfaces on top of Python’s `argparse`.

Define apps with `Parser`, `Argument`, and `Command` — same argument syntax you
already know, plus optional components for views, logging, config, and shell
completion.

## Start here

1. [Install](quickstart/install.md) — `pip install mrjk.clak`
2. [Quickstart](quickstart/quickstart.md) — a two-command hello world
3. [Getting started guide](guides/guide_101.md) — arguments step by step

Then pick what you need:

| I want to… | Go to |
| --- | --- |
| Build nested / git-like commands | [Nested commands](guides/guide_102.md) |
| Print tables / JSON from commands | [Views](docs/views.md) |
| Add `-v` logging | [Logging](docs/logging.md) |
| Load XDG config files | [Config](docs/config.md) |
| Ship shell tab-completion scripts | [Completion](docs/completion.md) |
| Handle errors with exit codes | [Error handling](docs/exceptions.md) |
| Paste context into an AI chat | [AI primer](ai/primer.md) · [AI reference](ai/reference.md) |
| See what is planned | [Roadmap](project/roadmap.md) |

## Why Clak?

- **Argparse-native** — no new DSL; `Argument(...)` mirrors `add_argument(...)`
- **Class-based** — inheritance and composition for real apps
- **Optional batteries** — mix in views, logging, config, completion only when useful

Feature overview: [Features](docs/features.md). Design notes:
[Architecture](architecture/list.md).
