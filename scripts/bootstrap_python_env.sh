#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

for arg in "$@"; do
  case "$arg" in
    --with-pdf)
      # Backward-compatible no-op: PDF support is installed by default.
      ;;
    *)
      echo "unknown option: $arg" >&2
      echo "usage: scripts/bootstrap_python_env.sh [--with-pdf]" >&2
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install beautifulsoup4 liteparse lxml requests

.venv/bin/python scripts/paper_translator.py doctor --json
