#!/usr/bin/env bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT" || exit 1
bash check.sh
if ! uv run --offline --frozen --no-sync python grader/gate.py; then
  failed=$(uv run --offline --frozen --no-sync python -c 'import json; print(", ".join(x["name"] for x in json.load(open("results/report.json"))["results"] if x["status"] != "pass"))')
  echo "WARNING: gate failed; failing checks: $failed. Continuing submission with partial work."
fi
# Stage only what exists. HANDOFF.md is no longer shipped, and a missing path
# would abort the whole submission.
for p in AGENTS.md app tests grader results reports docs TASKS.md README.md \
         check.sh init.sh submit.sh pyproject.toml uv.lock .github; do
  [ -e "$p" ] && git add "$p"
done
# The execution skill git-ignores its own workspace, so the ledger needs -f.
for p in .superpowers progress.md; do
  [ -e "$p" ] && git add -f "$p"
done
if ! git diff --cached --quiet; then git commit -m "w12_red_green_lab submission" || exit 1; fi
branch=$(git branch --show-current)
git push -u origin "$branch" || { echo "Push failed. Partial work remains committed locally."; exit 1; }
