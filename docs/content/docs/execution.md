# Shipping your CLI

Ways to run a Clak app from the command line — from a local script to an
installed console entry point.

- Call with the Python interpreter: `python script.py …`
- Make the file executable on Unix-like systems
- Package as a `console_scripts` / Poetry / PDM / UV entry point

Clak does not replace packaging; it replaces hand-rolled argparse wiring inside
your `main`.


## Without package managers


### With the Python interpreter

1. Create your script (Clak example):

   ```python
   #!/usr/bin/env python3
   from clak import Argument, Parser

   class App(Parser):
       """Hello CLI."""
       name = Argument("NAME", nargs="?", default="World")

       def cli_run(self, name="World", **_):
           print(f"Hello, {name}")

   if __name__ == "__main__":
       App()
   ```

2. Run it:

```bash
python script.py --help
python script.py Ada
```

### As an executable script

1. Keep the shebang (`#!/usr/bin/env python3`).
2. `chmod +x script.py`
3. Run `./script.py --help` (or put the directory on `$PATH`).


## With package managers

Expose a function that constructs your root `Parser` (instantiation runs
dispatch). Prefer returning/`sys.exit`ing an int only if you call `dispatch`
yourself with `parse=False` patterns; for the default `App()` style, the
entry point can simply construct the app.

### Setuptools

```python
# your_package/__main__.py or cli.py
from your_package.app import App

def main():
    App()
```

```python
# setup.py
from setuptools import setup

setup(
    name="your-package",
    version="0.1.0",
    packages=["your_package"],
    entry_points={
        "console_scripts": [
            "your-command=your_package.cli:main",
        ],
    },
)
```

```bash
pip install -e .
your-command --help
```

### Poetry

```toml
[tool.poetry.scripts]
your-command = "your_package.cli:main"
```

```bash
poetry install
poetry run your-command --help
```

### PDM / UV

```toml
[project.scripts]
your-command = "your_package.cli:main"
```

```bash
pdm install && pdm run your-command --help
# or
uv pip install -e . && your-command --help
```


### Best practices

1. Use a clear command name that does not collide with system tools.
2. Rely on Clak/`argparse` help instead of a custom usage printer.
3. Raise `ClakUserError` (or your app errors) and let Clak set exit codes —
   see [Error handling](exceptions.md).
4. For tab completion after install, emit a script with
   [Completion](completion.md) using the installed executable name.
