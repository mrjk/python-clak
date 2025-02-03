# Features

- Argparse friendly:
  - Reuse as much as possible from argparse, but allow a new modular way to built CLI.
  - If you know argparse, then you already know how to use clak.
  - Same API:
    - `argparse.ArgumentParser()` becomes `class MyApp(Parser):`
    - `.add_argument(...)` becomes `dest = Argument(...)`
    - `.add_subparser(...)` becomes `subcmd1 = SubCommand(...)`
  - Extended API:
    - `.add_argument("--option", "o", help="Optional argument")` => `option = Opt("--option", "o", help="Optional argument")`
    - `.add_argument("param", help="Positional argument")` => `param = Arg(help="Positional argument")`
    - `.add_suparser(...)` => `subcmd1 = Cmd(ChildrenParserClass, help="Subcommand help")`

- Class based approach:
  - Use Python class to provide declarative command line.
  - Since we use class, we can take advantage of Python inheritance to create CLI.
    - Including organizing command in a tree structure.
    - Inherit and share settings among different class, to allow maximum reusability.
  - Hide internal argparse implementation from user, so you can focus on your app.

- Build git-like CLI with ease
  - Rely on arparse subparser functionality.
  - Pythonic class based approach to represent.
  - Each subcommands are `Parser` instances, referenced via the `SubCommand` field.

- Easy sub-command discovery
  - All possible command are show in the root help
  - All subcommands display indiviudal and customizable help message.

- Modular components and reusable components:
  - Help:
    - Comprehensive help message with command tree display.
    - Manage `--help` and `-h` flags.
    - Easily change usage, description or epilog
  - Logging:
    - Configure and enable Basic Logger
    - Provide per Node logger
    - Provide `--verbose` and `-v,-vv,-vvv` flags
  - Config:
    - Use XDG Base Directory Specification to provide config files and directory paths.
    - Load yaml, json, toml, ini files easily
  - Completion:
    - Provide `completion` or `--complete` flag to generate completion script.
    - Support most common shell via the `argcomplete` library.
  - More to come ...
    - Environment var support
    - Automatic app config reader/writer
  - Build your own:
    - Reuse your existing code, your favorite CLI options, put them in a library and ship it.
