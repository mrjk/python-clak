#!/usr/bin/env bash
# Bootstrap mise-pinned tools and the project in-project .venv.
# Installs Poetry groups needed for local `task test` (dev + docs).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v mise >/dev/null 2>&1; then
  echo "error: mise not found on PATH. Activate mise first:" >&2
  echo "  eval \"\$(mise activate bash)\"   # or: eval \"\$(mise activate zsh)\"" >&2
  echo "See docs/content/project/setup.md" >&2
  exit 1
fi

echo "Installing mise tools …"
mise install

poetry_bin="$(mise which poetry)"
python_bin="$(mise which python)"

echo "Configuring Poetry env: ${python_bin}"
"$poetry_bin" env use "$python_bin"

echo "Installing project deps (dev + docs) …"
"$poetry_bin" install --with dev,docs --no-interaction

echo "Setup complete. Next: task test_pytest"
