# Release

Maintainer guide to bump, tag, and publish `mrjk-clak` to PyPI.

## Overview

| Step | Command |
|------|---------|
| Bump + tag | `./scripts/release.sh <VERSION>` |
| Push | `git push && git push --tags` |
| Publish | automatic on `v*` tag (or `task publish_pypi`) |

Version lives in `pyproject.toml`. Install the bump plugin once with
`poetry self add poetry-bumpversion` so `poetry version` also updates
`clak/__init__.py` (see `[tool.poetry_bumpversion]` in `pyproject.toml`).

Override the package directory if needed: `PKG_DIR=clak ./scripts/release.sh patch`.

## Prerequisites

- Clean git working tree (untracked files are fine; modified/staged files are not)
- Tools via mise (`mise install`) and Poetry project deps (`poetry install --with dev`)
- For stable releases: checkout `main` or `master`
- For pre-releases (`pre*`, or a version like `1.2.3a0`): any branch **except** `main`/`master` (usually `develop`)
- For automated publish: repository secret `PYPI_TOKEN` and (optional) environment `pypi`

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

Pushing a `v*` tag runs `.github/workflows/publish_pypi.yml`: `task test` on
Python 3.10 + 3.12, then `task publish_pypi` using `PYPI_TOKEN`.

See `./scripts/release.sh --help` for all bump keywords.

## PyPI authentication

### CI (recommended)

Create a PyPI API token at
[pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
and store it as the repository secret `PYPI_TOKEN`.

### Local / manual

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

**Next alpha on develop**

```bash
./scripts/release.sh prerelease
git push && git push --tags   # tag triggers CI publish
```

**Stable release**

```bash
git checkout main && git pull
./scripts/release.sh patch
git push && git push --tags
```

**Manual publish** (if CI secret is not set)

```bash
task publish_pypi
```

## CI toolkit (reuse)

Portable **CORE** (copy to other small Poetry projects):

- `mise.toml` — pin python / task / poetry / shellcheck
- `ci/Taskfile.core.yml` — `test_core`, lint, publish
- `.github/actions/setup-ci/` — shared mise + Poetry bootstrap
- `.github/workflows/test_project.yml` — thin `poetry run task test`
- `scripts/release.sh` — bump + tag (`PKG_DIR=…`)

**OPTIONAL** (keep project-specific): root `Taskfile.yml` regressions,
`docs/Taskfile.yml`, docs/publish workflows.

Validate locally:

```bash
mise install
poetry install --with dev
bash ci/smoke_core.sh
task test_core    # portable gate
task test         # full Clak gate
```
