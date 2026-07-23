#!/usr/bin/env bash
# Run pytest across Python versions using mise + isolated .venvs/pyX.Y.
# Does not touch the default Poetry .venv. Extra Pythons are installed only here.
# Avoids `source activate`; uses explicit venv bin paths + VIRTUAL_ENV.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENVS_DIR="${VENVS_DIR:-.venvs}"
DEFAULT_MATRIX="3.10 3.11 3.12 3.13 3.14"

if [[ -n "${PYTHON_VERSION:-}" ]]; then
  VERSIONS=("$PYTHON_VERSION")
elif [[ -n "${PYTHON_MATRIX:-}" ]]; then
  # shellcheck disable=SC2206
  VERSIONS=($PYTHON_MATRIX)
else
  # shellcheck disable=SC2206
  VERSIONS=($DEFAULT_MATRIX)
fi

if ! command -v mise >/dev/null 2>&1; then
  echo "error: mise is required (https://mise.jdx.dev/)" >&2
  exit 1
fi

if ! command -v poetry >/dev/null 2>&1; then
  echo "error: poetry is required on PATH" >&2
  exit 1
fi

mkdir -p "$VENVS_DIR"

venv_major_minor() {
  local venv_py="$1"
  "$venv_py" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
}

# Resolve interpreter for a version. Prefer `mise which --tool=`; fall back to `mise where`.
resolve_python() {
  local ver="$1"
  local py="" prefix=""

  if py="$(mise which python --tool="python@${ver}" 2>/dev/null)" && [[ -x "$py" ]]; then
    printf '%s\n' "$py"
    return 0
  fi

  prefix="$(mise where "python@${ver}")"
  py="${prefix}/bin/python"
  if [[ -x "$py" ]]; then
    printf '%s\n' "$py"
    return 0
  fi

  echo "error: could not resolve python@${ver} (tried mise which --tool= and mise where)" >&2
  return 1
}

with_matrix_venv() {
  local venv_dir="$1"
  shift
  local venv_abs
  venv_abs="$(cd "$venv_dir" && pwd)"
  env VIRTUAL_ENV="$venv_abs" \
    PATH="${venv_abs}/bin:${PATH}" \
    POETRY_VIRTUALENVS_CREATE=false \
    "$@"
}

ensure_venv() {
  local ver="$1"
  local venv_dir="$VENVS_DIR/py${ver}"
  local py

  echo "Installing mise python@${ver} (if needed)…"
  mise install "python@${ver}"

  py="$(resolve_python "$ver")"
  echo "Using interpreter: ${py}"

  if [[ -x "${venv_dir}/bin/python" ]]; then
    local current
    current="$(venv_major_minor "${venv_dir}/bin/python")"
    if [[ "$current" != "$ver" ]]; then
      echo "Recreating ${venv_dir} (was ${current}, want ${ver})"
      rm -rf "$venv_dir"
    fi
  fi

  if [[ ! -x "${venv_dir}/bin/python" ]]; then
    echo "Creating ${venv_dir}"
    "$py" -m venv "$venv_dir"
  fi

  echo "poetry install into ${venv_dir}"
  with_matrix_venv "$venv_dir" poetry install --with dev --without docs --no-interaction
}

run_tests() {
  local ver="$1"
  local venv_dir="$VENVS_DIR/py${ver}"
  local pytest_bin="${venv_dir}/bin/pytest"

  if [[ ! -x "$pytest_bin" ]]; then
    echo "error: pytest not found in ${venv_dir} (poetry install failed?)" >&2
    return 1
  fi

  echo "=== pytest (unit + regressions) @ ${ver} ==="
  with_matrix_venv "$venv_dir" env CLAK_COLORS=false \
    "$pytest_bin" tests/ -vv --tags unit-tests examples-unit examples-regressions

  echo "=== pytest (examples-regressions) @ ${ver} ==="
  with_matrix_venv "$venv_dir" env CLAK_COLORS=false \
    "$pytest_bin" tests/ --tags examples-regressions

  echo "=== pytest (examples-regressions-cli) @ ${ver} ==="
  with_matrix_venv "$venv_dir" env CLAK_COLORS=false \
    "$pytest_bin" tests/ --tags examples-regressions-cli
}

FAILED=()
PASSED=()

for ver in "${VERSIONS[@]}"; do
  echo
  echo "########################################"
  echo "# Python ${ver}"
  echo "########################################"
  # Subshell keeps set -e effective (unlike `if cmd`; failures must not continue into poetry/default env).
  if (
    set -euo pipefail
    ensure_venv "$ver"
    run_tests "$ver"
  ); then
    PASSED+=("$ver")
  else
    FAILED+=("$ver")
  fi
done

echo
echo "======== matrix summary ========"
echo "passed: ${PASSED[*]:-none}"
echo "failed: ${FAILED[*]:-none}"

if [[ ${#FAILED[@]} -gt 0 ]]; then
  exit 1
fi
