# Installation


## Requirements

Clak supports **Python 3.10–3.14**. Packaging declares `requires-python = ">=3.10,<4.0"`.


## Package installation

Clak is a Python library. Install it with any of the following methods.


### Install with pip

!!! tip
    Recommended for quickstart and evaluation.

```bash
pip install mrjk.clak
```

### Install with package managers

!!! tip
    Recommended for production use.

```bash
poetry add mrjk.clak
pdm add mrjk.clak
uv add mrjk.clak
```

### Install from git

!!! tip
    Recommended for development or testing a specific branch.

```bash
# Development branch
pip install git+https://github.com/mrjk/python-clak.git@develop

# Stable default branch
pip install git+https://github.com/mrjk/python-clak.git
```


## Optional extras

### Colors

Colored log output for `LoggingOptMixin` (via `coloredlogs`):

```bash
pip install 'mrjk.clak[colors]'
```

Or set `CLAK_COLORS=0` to disable colors even when `coloredlogs` is installed.

### Config / YAML

YAML config files for `XDGConfigMixin`, and YAML output for views
(`--format yaml`), need PyYAML:

```bash
pip install 'mrjk.clak[config]'
```

JSON config files and `--format json` / `csv` work without extras (stdlib).


## Shell completion helper

`argcomplete` is already a dependency of Clak. To activate it for many Python
CLIs on a machine (optional, once):

```bash
activate-global-python-argcomplete
```

See [Shell completion](completion.md) for generating a script for your app.
