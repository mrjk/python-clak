# Release

Maintainer guide to bump, tag, and publish `mrjk-clak` to PyPI.

## Overview

| Step | Command |
|------|---------|
| Bump + tag | `./scripts/release.sh <VERSION>` |
| Push | `git push && git push --tags` |
| Publish | `task publish_pypi` |

Version lives in `pyproject.toml`. `poetry-bumpversion` also updates `clak/__init__.py` when Poetry bumps the version.

## Prerequisites

- Clean git working tree (untracked files are fine; modified/staged files are not)
- Poetry installed and project deps available
- For stable releases: checkout `main` or `master`
- For pre-releases (`pre*`, or a version like `1.2.3a0`): any branch **except** `main`/`master` (usually `develop`)

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

Publishing needs a PyPI API token. Create one at
[pypi.org/manage/account/token/](https://pypi.org/manage/account/token/).

Persist with Poetry:

```bash
poetry config pypi-token.pypi pypi-AgEIcHlwaS5vcmc...
```

Or for a single publish (no config file):

```bash
export POETRY_PYPI_TOKEN_PYPI=pypi-AgEIcHlwaS5vcmc...
task publish_pypi
```

If you see `HTTP 403` / access denied, the token is missing or revoked — reconfigure as above.

### TestPyPI

One-time repository + token setup:

```bash
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi pypi-...   # token from test.pypi.org
```

## Publish

```bash
task publish_pypi_test   # test.pypi.org (needs testpypi config above)
task publish_pypi        # pypi.org
```

These tasks run `poetry build` then `poetry publish`.

## Typical flows

**Next alpha on develop**

```bash
./scripts/release.sh prerelease
git push && git push --tags
task publish_pypi
```

**Stable release**

```bash
git checkout main && git pull
./scripts/release.sh patch   # or an explicit version
git push && git push --tags
task publish_pypi
```
