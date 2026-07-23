# Development setup

How to run Clak locally and across supported Python versions.

## Prerequisites

- [mise](https://mise.jdx.dev/) — pins the default Python (and other tools when configured)
- [Poetry](https://python-poetry.org/) — project dependencies
- [Task](https://taskfile.dev/) — `task test`, lint, docs, matrix

Supported range: **Python 3.10–3.14**. Daily development uses **3.12** (`mise.toml`).

## Bootstrap (daily env)

`mise.toml` pins **only** 3.12. A normal `mise install` does **not** download other Python versions.

```bash
mise install
poetry env use "$(mise which python)"
poetry install
```

Run the full local suite (default Poetry `.venv`):

```bash
task test
```

Useful subsets:

| Task | What it runs |
|------|----------------|
| `task test_pytest` | Unit + example unit/regression tags |
| `task test_regressions` | Example regressions (incl. CLI; `CLAK_COLORS=false`) |
| `task test_lint_full` | Lint + docs checks |
| `task fix_regressions` | `pytest --force-regen` for regression fixtures |

## Local Python matrix

To exercise 3.10–3.14 without switching the default `.venv`, use isolated envs under `.venvs/pyX.Y`. Other Pythons are installed **on demand** when you run the matrix (via `mise install python@$ver`). The script does **not** `source activate`; it points Poetry/pytest at each venv with `VIRTUAL_ENV` + `PATH`.

```bash
task test_matrix                       # all of 3.10–3.14
task test_matrix_one PYTHON_VERSION=3.11
```

Override the set with `PYTHON_MATRIX` if needed:

```bash
PYTHON_MATRIX="3.12 3.13" bash ./scripts/run_python_matrix.sh
```

Implementation: [`scripts/run_python_matrix.sh`](https://github.com/mrjk/python-clak/blob/develop/scripts/run_python_matrix.sh).  
`.venvs/` is gitignored and never replaces Poetry’s `.venv`. If a previous failed run left empty dirs, remove them: `rm -rf .venvs/py3.10` (etc.).

## CI

GitHub Actions runs the same version range as a **matrix** (one job per Python) for the Actions UI. Local `task test_matrix` complements that; it does not replace CI.

See [`.github/workflows/test_project.yml`](https://github.com/mrjk/python-clak/blob/develop/.github/workflows/test_project.yml).

## Releases

Maintainer bump/tag/publish: [Release](release.md).
