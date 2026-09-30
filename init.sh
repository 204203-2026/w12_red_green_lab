#!/usr/bin/env bash
# Setup may use network once. All lab checks run offline afterwards.
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT" || exit 1
missing=0
for tool in git python3 uv; do
  command -v "$tool" >/dev/null 2>&1 || { echo "MISSING $tool"; missing=$((missing + 1)); }
done
[ "$missing" -eq 0 ] || exit 1
uv sync --frozen || exit 1
uv run python -c 'from app.main import ensure_database; ensure_database()' || exit 1
mkdir -p results
echo "OK offline fixture ready. Run: uv run --offline --frozen pytest -q"
