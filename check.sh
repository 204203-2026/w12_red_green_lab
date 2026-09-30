#!/usr/bin/env bash
# Week 12 self-check. No set -e; report JSON, not shell exit, carries grade.
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT" || exit 0
export UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never
mkdir -p results
PASS=0; FAIL=0; TOTAL=0; BONUS=0; BONUS_DONE=0; REQ_ITEMS=""; BONUS_ITEMS=""
record() { TOTAL=$((TOTAL + 1)); if [ "$2" = PASS ]; then PASS=$((PASS + 1)); status=pass; else FAIL=$((FAIL + 1)); status=fail; fi; REQ_ITEMS="${REQ_ITEMS}{\"name\":\"$1\",\"status\":\"$status\"},"; echo "$2 $1 - $3"; }
record_bonus() { BONUS=$((BONUS + 1)); if [ "$2" = DONE ]; then BONUS_DONE=$((BONUS_DONE + 1)); status=bonus; else status=todo; fi; BONUS_ITEMS="${BONUS_ITEMS}{\"name\":\"$1\",\"status\":\"$status\"},"; echo "$2 $1 (optional) - $3"; }
required() { if uv run --offline --frozen --no-sync python grader/check.py "$1"; then record "$1" PASS "$2"; else record "$1" FAIL "$2"; fi; }
bonus() { if uv run --offline --frozen --no-sync python grader/check.py "$1"; then record_bonus "$1" DONE "$2"; else record_bonus "$1" TODO "$2"; fi; }
required baseline_green "shipped baseline suite passes"
required student_tests_exist "three real /api/stats tests exist"
required oracle_stub "student tests assert against missing-feature stub"
required oracle_reference "student tests pass reference implementation"
required oracle_mutant_a "student tests kill rounded/off-by-one mutant"
required oracle_mutant_b "student tests kill fraction-scale mutant"
required red_before_green "git proves tests failed before implementation"
required app_green "independent stats contract passes"
required agents_md "AGENTS.md locks tests/"
required superpowers_used "Superpowers installed, evidence in reports/superpowers.md"
required superpowers_plan "writing-plans produced docs/superpowers/plans/YYYY-MM-DD-*.md"
required superpowers_progress "executing-plans kept the progress.md ledger"
bonus extra_mutants "extra mutants killed"
bonus injected_contract "STATS_BASE_URL contract test"
bonus warnings_clean "pytest warning-clean"
for report in results/report.json results/challenge_report.json; do if [ -e "$report" ]; then backup=$(mktemp -d results/.backup.XXXXXX); cp -p "$report" "$backup/$(basename "$report")"; fi; done
printf '{"score":%s,"total":%s,"results":[%s]}\n' "$PASS" "$TOTAL" "${REQ_ITEMS%,}" > results/report.json
printf '{"bonus":%s,"bonus_total":%s,"results":[%s]}\n' "$BONUS_DONE" "$BONUS" "${BONUS_ITEMS%,}" > results/challenge_report.json
echo "Score: $PASS / $TOTAL required | $FAIL failed | Bonus: $BONUS_DONE / $BONUS"
exit 0
