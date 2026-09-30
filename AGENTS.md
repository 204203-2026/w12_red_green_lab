# Week 12 agent rules

## Testing rules

- Do not edit `tests/` after tests are committed and locked.
- Write `tests/test_stats.py` before implementing `/api/stats`.
- Run `uv run --offline --frozen pytest -q` after every implementation change.

## Commit rules (Conventional Commits)

- Write every commit message as `type: short description`.
- `test:` for a commit that only adds or changes tests (the red).
- `feat:` for a commit that makes tests pass (the green).
- `fix:` for a bug fix, `refactor:` for a behavior-preserving change, `chore:` for setup or config.
- One kind of change per commit. Never put a test and its implementation in the same commit.
