# Release

Maintainer guide to bump, tag, and publish `mrjk.clak` to PyPI.

## Overview

| Step | Command |
|------|---------|
| Bump + tag | `task release` / `task pre-release` (preview: `*-show`) |
| Push | `git push && git push --tags` |
| Publish | CI on `v*` tags (or `task publish_pypi` manually) |

Version lives only in `pyproject.toml`. `clak.__version__` is read at import
from installed package metadata (`importlib.metadata.version("mrjk.clak")`).

Pushing a `v*` tag runs `.github/workflows/publish_pypi.yml`: test gate, then
`task publish_pypi`. Requires a GitHub environment named `pypi` with secret
`PYPI_TOKEN` (PyPI API token).

## Prerequisites

- Clean git working tree for a real bump (untracked files are fine; modified/staged files are not). `task *-show` dry-runs warn on a dirty tree instead of failing.
- Poetry project deps on the **daily Python 3.12** env (in-project **`.venv/`** via `poetry install --with dev`)
- For stable releases: checkout `main` or `master`
- For pre-releases (`pre*`, or a version like `1.2.3a0`): any branch **except** `main`/`master` (usually `develop`)
- For CI publish: GitHub environment `pypi` + secret `PYPI_TOKEN`
- For local/manual publish: a PyPI API token (`poetry config` or `POETRY_PYPI_TOKEN_PYPI`)

Supported runtime range for users: **Python 3.10–3.14** (see [Development setup](setup.md)).

## Bump and tag

Preview:

```bash
task pre-release-show
task release-show
```

Apply:

```bash
# Pre-release on develop (e.g. 0.4.0a2 -> 0.4.0a3)
task pre-release

# Next pre-release phase (a -> b -> rc -> final)
task pre-release -- --next-phase

# Stable on main/master (default: patch)
task release                  # or: task release -- minor | major | 1.2.3
```

These tasks wrap `./scripts/release.sh`, which:

1. Checks branch rules and clean tree
2. Runs `poetry version …`
3. Commits with `bump: version vX.Y.Z`
4. Creates annotated tag `vX.Y.Z`

Then push:

```bash
git push && git push --tags
```

See `./scripts/release.sh --help` for all bump keywords.

## PyPI authentication

### CI (default)

Configure once in the GitHub repo:

1. Environment: `pypi`
2. Environment **secret** (not a variable): `PYPI_TOKEN`
3. Value: a PyPI **API token** from
   [pypi.org/manage/account/token](https://pypi.org/manage/account/token/)
   (must start with `pypi-`; not a password; not a TestPyPI token)

On `v*` tag push, the workflow configures Poetry with that token and runs
`poetry run task publish_pypi`.

If publish fails with `403 Invalid or non-existent authentication information`,
the secret is usually missing/empty, misnamed, stored as a variable, or not a
live `pypi-…` token for pypi.org.

### Local / manual

```bash
poetry config pypi-token.pypi pypi-AgEIcHlwaS5vcmc...
# or:
export POETRY_PYPI_TOKEN_PYPI=pypi-AgEIcHlwaS5vcmc...
task publish_pypi
```

If you see `HTTP 403` / access denied, the token is missing or revoked.

### TestPyPI

`task publish_pypi_test` configures the TestPyPI repository URL. You still need
a token:

```bash
poetry config pypi-token.testpypi pypi-...   # token from test.pypi.org
# or:
export POETRY_PYPI_TOKEN_TESTPYPI=pypi-...
task publish_pypi_test
```

## Typical flows

### Next alpha on develop

```bash
task pre-release
git push && git push --tags
# CI publishes on the v* tag
```

### Stable release

```bash
git checkout main && git pull
task release
git push && git push --tags
# CI publishes on the v* tag
```

Manual override (local or recovery): `task publish_pypi`.
