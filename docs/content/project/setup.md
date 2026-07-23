# Development setup

How to run Clak locally and across supported Python versions.

## Supported Python versions

| | Version |
| --- | --- |
| **Supported** | **3.10, 3.11, 3.12, 3.13, 3.14** |
| Declared in packaging | `requires-python = ">=3.10,<4.0"` (`pyproject.toml`) |
| Daily / release base | **3.12** (`mise.toml`) |
| CI | GitHub Actions matrix over 3.10–3.14 |
| Docs build (CI) | 3.10 |

Tested continuously via [`.github/workflows/test_project.yml`](https://github.com/mrjk/python-clak/blob/develop/.github/workflows/test_project.yml) and locally with `task test_matrix`.

## Virtualenvs (always)

Development **always** uses a project-local virtualenv — never install into the system Python.

| Env | Path | Role |
| --- | --- | --- |
| Daily / release | **`.venv/`** | Poetry in-project env (`poetry.toml`: `virtualenvs.in-project = true`) |
| Version matrix | **`.venvs/pyX.Y/`** | Isolated envs for `task test_matrix` (does not replace `.venv`) |

Both directories are gitignored.

## Prerequisites

- [mise](https://mise.jdx.dev/) — pins **Python 3.12**, **Poetry**, and **Task** (`mise.toml`)
- A shell with mise activated (`eval "$(mise activate bash)"`, or direnv + `use mise` in `.envrc`)

Poetry and Task come from mise after `mise install` — you do **not** need a system-wide Poetry install.

## Bootstrap (daily env)

`mise.toml` pins the daily toolchain. A normal `mise install` does **not** download other Python versions (those come with the matrix).

```bash
# 1) Activate mise in this shell (skip if direnv already loaded .envrc)
eval "$(mise activate bash)"   # or: eval "$(mise activate zsh)"

# 2) Install pinned tools (python 3.12, poetry, task)
mise install
mise which poetry              # should print a path under ~/.local/share/mise/...

# 3) Create/update project .venv
poetry env use "$(mise which python)"
poetry install --with dev
```

After bootstrap, run Task as usual — Python tools are invoked via `poetry run`
(see `PY` in the root Taskfile), so you do **not** need to activate `.venv`:

```bash
task test
task fix_lint
```

`poetry` itself must be on your PATH (from `mise activate` / `.envrc`).

Useful subsets:

| Task | What it runs |
|------|----------------|
| `task test_pytest` | Unit + example unit/regression tags |
| `task test_regressions` | Example regressions (incl. CLI; `CLAK_COLORS=false`) |
| `task test_lint_full` | Lint + docs checks |
| `task fix_regressions` | `pytest --force-regen` for regression fixtures |
| `task clean` | Remove `.venv`, `.venvs`, caches, build artifacts |

## Reset environment (fresh-clone-like)

Removes local virtualenvs and generated artifacts only — **not** git history, source, or mise-installed tools.

```bash
task clean
```

What it deletes (see `scripts/clean_workspace.sh`):

- `.venv/`, `.venvs/`
- `dist/`, `build/`, `*.egg-info`
- `__pycache__/`, `.pytest_cache/`, coverage and similar caches
- `docs/site/`, `.cache/`

Then bootstrap again:

```bash
eval "$(mise activate bash)"   # if needed
mise install
poetry env use "$(mise which python)"
poetry install --with dev
```

## Local Python matrix

To exercise 3.10–3.14 without touching daily `.venv`, use isolated envs under `.venvs/pyX.Y`. Other Pythons are installed **on demand** when you run the matrix (via `mise install python@$ver`). The script does **not** `source activate`; it points Poetry/pytest at each venv with `VIRTUAL_ENV` + `PATH`.

```bash
task test_matrix                       # all of 3.10–3.14
task test_matrix_one PYTHON_VERSION=3.11
```

Override the set with `PYTHON_MATRIX` if needed:

```bash
PYTHON_MATRIX="3.12 3.13" bash ./scripts/run_python_matrix.sh
```

On **3.14**, installing some lockfile deps (e.g. `rpds-py` via PyO3) needs:

```bash
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
```

The matrix script and CI already set this. Remove it once upstream PyO3 advertises 3.14 support.

Implementation: [`scripts/run_python_matrix.sh`](https://github.com/mrjk/python-clak/blob/develop/scripts/run_python_matrix.sh).  
If a previous failed run left empty dirs, remove them: `rm -rf .venvs/py3.10` (etc.).

## CI

GitHub Actions also uses an in-project `.venv` (`virtualenvs-in-project: true`) and runs the same Python matrix. Local `task test_matrix` complements that; it does not replace CI.

See [`.github/workflows/test_project.yml`](https://github.com/mrjk/python-clak/blob/develop/.github/workflows/test_project.yml).

## Releases

Bump/tag/publish uses the **3.12** daily `.venv`. Maintainer guide: [Release](release.md).
