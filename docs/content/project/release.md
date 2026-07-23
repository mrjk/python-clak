# Release

Maintainer guide to bump, tag, and publish `mrjk.clak` to PyPI.

## Overview

| Step | Command |
|------|---------|
| Bump + tag | `./scripts/release.sh <VERSION>` |
| Push | `git push && git push --tags` |
| Publish | `task publish_pypi` (manual today) |

Version lives in `pyproject.toml`. Install the bump plugin once with
`poetry self add poetry-bumpversion` so `poetry version` also updates
`clak/__init__.py` (see `[tool.poetry_bumpversion]` in `pyproject.toml`).

Override the package directory if needed: `PKG_DIR=clak ./scripts/release.sh patch`.

Automated publish-on-tag is tracked on the [roadmap](roadmap.md).

## Prerequisites

- Clean git working tree (untracked files are fine; modified/staged files are not)
- Poetry project deps on the **daily Python 3.12** env (`mise.toml` / `poetry install --with dev`)
- For stable releases: checkout `main` or `master`
- For pre-releases (`pre*`, or a version like `1.2.3a0`): any branch **except** `main`/`master` (usually `develop`)
- For publish: a PyPI API token (`poetry config` or `POETRY_PYPI_TOKEN_PYPI`)

Supported runtime range for users: **Python 3.10–3.14** (see [Development setup](setup.md)).

## Bump and tag

Preview:

```bash
./scripts/release.sh --dry-run prerelease
./scripts/release.sh --dry-run patch
```

Apply:

```bash
# Pre-release on develop (e.g. 0.4.0a2 -> 0.4.0a3)
./scripts/release.sh prerelease

# Next pre-release phase (a -> b -> rc -> final)
./scripts/release.sh prerelease --next-phase

# Stable on main/master
./scripts/release.sh patch    # or: minor | major | 1.2.3
```

The script:

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

### Local / manual (current)

```bash
poetry config pypi-token.pypi pypi-AgEIcHlwaS5vcmc...
# or:
export POETRY_PYPI_TOKEN_PYPI=pypi-AgEIcHlwaS5vcmc...
task publish_pypi
```

If you see `HTTP 403` / access denied, the token is missing or revoked.

### TestPyPI

```bash
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi pypi-...   # token from test.pypi.org
task publish_pypi_test
```

## Typical flows

### Next alpha on develop

```bash
./scripts/release.sh prerelease
git push && git push --tags
task publish_pypi
```

### Stable release

```bash
git checkout main && git pull
./scripts/release.sh patch
git push && git push --tags
task publish_pypi
```
