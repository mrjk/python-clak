#!/usr/bin/env bash
# Remove local virtualenvs, caches, and build artifacts so the tree looks
# like a fresh git clone (source + lockfiles kept; tools from mise untouched).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Cleaning workspace artifacts under ${ROOT_DIR} …"

# Virtualenvs
rm -rf .venv .venvs

# Packaging / install leftovers
rm -rf dist build .eggs
find . -maxdepth 3 -type d \( -name '*.egg-info' -o -name '*.eggs' \) \
  -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true

# Test / lint / coverage caches
rm -rf .pytest_cache .mypy_cache .ruff_cache .tox .hypothesis htmlcov
rm -f .coverage
rm -f .coverage.*

# Bytecode
find . -type d -name '__pycache__' -not -path './.git/*' -print0 \
  | xargs -0r rm -rf

# Docs / local tool caches in-repo
rm -rf docs/site .cache

echo "Done. Source and lockfiles were kept."
echo "Re-bootstrap:"
echo "  eval \"\$(mise activate bash)\"   # if needed"
echo "  mise install"
echo "  poetry env use \"\$(mise which python)\""
echo "  poetry install --with dev"
