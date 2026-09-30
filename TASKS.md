# w12_red_green_lab — TDD with Superpowers

**This week, you study the plugin.** You install [Superpowers](https://github.com/obra/superpowers). You give it a feature. It plans the work. It requires a real failing run before each task writes code. Red-before-green helps you understand its work. It also lets you give it the implementation work.

Study by yourself. On Friday we are in the room for 2 hours if you want help. The grader reads the last CI run before Monday 5 October 23:59.

**Scoring:** There are 12 required checks. Each is worth 1 point (`results/report.json`). Bonus results are in `results/challenge_report.json`. They never affect the grade.

This week uses a different agent workflow. Your tests are the graded oracle. The grader runs your `tests/test_stats.py` against several app versions. These include the shipped stub and your implementation. They also include mutants. Each mutant is a copy of your implementation with one planned bug. A test passing only on your machine is not evidence.

**Who writes what — read this once.** You must use **Codex** here. Step 2 is required. It is not optional. The Superpowers plugin drives the implementation. The split is:

| | who |
|---|---|
| `tests/test_stats.py` | **you** — write it from the contract below. Write it *before* the endpoint exists. Lock it once committed. |
| `app/main.py` (`/api/stats`) | **Codex**, driven by Superpowers (Step 2) |

You may use Codex to help draft the tests. Write them from the **contract table below**. Never write them from an implementation. Watch them fail before you give the work to Codex. A test written after code can repeat the same bugs. Then mutants can pass that test. Your grade depends on whether your tests tell a correct implementation from a broken one. You must write the tests yourself.

Every required check is offline. It gives the same result each time. Run this command everywhere:

```console
$ uv run --offline --frozen pytest -q
```

## Step 0 — Setup and see green (15 min)

```console
$ bash init.sh
$ uv run --offline --frozen pytest -q
$ bash check.sh
```

The baseline has two green tests. `/api/stats` returns HTTP 501 on purpose.

Troubleshooting:

- `uv` missing: install uv. Then rerun `bash init.sh` online once.
- Offline resolution fails: keep the shipped `uv.lock`. While online, run `uv sync --frozen` once.
- Baseline fails: rerun `bash init.sh`. Do not edit baseline tests.

## The `/api/stats` contract — read this before writing any test

`GET /api/stats` must return **HTTP 200** with exactly these three keys:

| key | type | meaning |
|---|---|---|
| `total` | int | every row in the `cards` table |
| `done` | int | rows whose `status` is exactly the string `done` |
| `percent_done` | float | `100.0 * done / total` — a percentage on a **0-100** scale |

The grader enforces four rules. You lose a required check if you get any rule wrong:

1. **`percent_done` is NOT rounded.** Return the raw float. If `3` of `7` are done, it must be `42.857142857142854`, not `42.86` and not `43`. A `round()` anywhere in your implementation will fail the grader's own contract check.
2. **The scale is 0-100, not 0-1.** Half done is `50.0`, never `0.5`.
3. **Zero cards must not crash.** If the table is empty, return `{"total": 0, "done": 0, "percent_done": 0.0}`. Return HTTP 200. Do not raise `ZeroDivisionError`. Do not return 500.
4. **`done` counts `status == "done"` exactly.** No other status counts.

### The seeded data, and the exact numbers it produces

`init.sh` seeds **4 cards, 2 of them `done`**. "Write tests" and "Lock red" are `done`. "Implement" and "Review" are `todo`. A correct implementation returns these values. Assert them as literals:

| state of the table | `total` | `done` | `percent_done` |
|---|---|---|---|
| as seeded | 4 | 2 | `50.0` |
| seeded + one `done` card | 5 | 3 | `60.0` |
| seeded + 3 `todo` cards | 7 | 2 | `28.571428571428573` |
| all cards deleted | 0 | 0 | `0.0` |

The third row finds a rounded implementation. **Include a case whose percentage is not a whole number.**

### Where the code lives, and the fixture you get

- Implement `GET /api/stats` in **`app/main.py`**. The stub already returns `501`. Replace only its body. Reuse the `database()` context manager used by the other routes in that file.
- `tests/conftest.py` gives you a `client` fixture. Use it as an argument. It gives you a `TestClient` for a **temporary copy** of the database. Each test starts with the seeded 4 cards. Your changes do not affect the next test:

```python
def test_something(client):          # just name the argument `client`
    response = client.get("/api/stats")
    assert response.status_code == 200
```

### How to change the table inside a test

`POST /cards` takes **query parameters, not a JSON body**. This differs from the Week 8 app. Use `params=`. Otherwise, you will get a silent `422`:

```python
client.post("/cards", params={"title": "extra", "status": "done"})   # 201
client.post("/cards", json={"title": "extra"})                       # 422 - wrong
```

There is no delete route. For the empty-table case, change the database directly. The `client` fixture in `tests/conftest.py` points the app at a temporary copy. This does not change your real data:

```python
import sqlite3
from app import main

def test_zero_cards(client):
    with sqlite3.connect(main.DB_PATH) as db:
        db.execute("DELETE FROM cards")
    body = client.get("/api/stats").json()
    assert body == {"total": 0, "done": 0, "percent_done": 0.0}
```

## What is already in the repo (read once)

- **`AGENTS.md` is already here. It already contains the testing rules.** "Never modify anything under `tests/`. The suite is the spec." Codex reads it at the start of every session. The rule applies without any action from you. The required `agents_md` check already passes. Do not delete or empty the file.
- `tests/test_app.py` — two baseline tests already pass. Leave them alone.
- `tests/conftest.py` — gives you the `client` fixture for your tests.
- `app/main.py` — the app. `/api/stats` is not written yet, on purpose (`501`).

## Step 1 — Write and lock stats tests (35 min)

Create `tests/test_stats.py` with at least three `test_` functions that call `GET /api/stats`. Cover the seeded counts. Cover a changed card mix **whose percentage is not a whole number**. Cover the empty table. Assert the exact status code. Assert the exact values from the contract table above as literals. Do not recompute arithmetic. Commit this test-only change now:

Here is one complete test. Write the other two yourself using the contract table above:

```python
# tests/test_stats.py
def test_seeded_counts(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json() == {"total": 4, "done": 2, "percent_done": 50.0}
```

`client` comes from `tests/conftest.py`. Name it as an argument. pytest gives it to you. It acts as a browser connected to the app. You do not need to start a server.

```console
$ git add tests/test_stats.py
$ git commit -m "test: specify stats endpoint"
$ uv run --offline --frozen pytest -q tests/test_stats.py
```

It must fail with assertions because 501 is correct starter behavior. Do not edit this file after you lock it.

Troubleshooting:

- Collection/import error: copy the fixture pattern from `tests/conftest.py`. Fix the test setup until the failure is `AssertionError`.
- Test passes: it does not test the endpoint contract. Assert the response status and values.
- Mutant survives: add a case with different arithmetic. Then recommit the test before implementation.

## Step 2 — Work the feature through Superpowers (45 min) — REQUIRED

This is this week's subject. **You do not implement `/api/stats` by hand.** Install a skills plugin. Let it run its development workflow using your locked tests. It works one task at a time: *plan → execute → test-driven development*.

### 2a. Install the plugin

From inside a Codex session:

```console
/plugins            # opens the plugin search interface
superpowers         # search, then choose: Install Plugin
```

or from the shell:

```console
$ codex plugin marketplace list                        # is it already configured?
$ codex plugin add superpowers@superpowers-marketplace
$ codex plugin list | grep superpowers
superpowers@claude-plugins-official   installed, enabled  6.4.1
```

### 2b. Make it write the plan

> **PROMPT — type this into Codex**
>
> ```text
> Use the writing-plans skill to plan the implementation of GET /api/stats.
> My tests in tests/test_stats.py are already locked and must not change.
> ```

The skill announces itself. Then it saves a plan to a fixed location: **`docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`**. Its header always uses `**Goal:**`, `**Architecture:**`, then numbered `## Task N:` sections. Each section is small enough to finish in a few minutes. Read the plan before it builds anything. This is the easiest time to find a wrong approach.

### 2c. Make it execute the plan, task by task

> **PROMPT — type this into Codex**
>
> ```text
> Use the executing-plans skill to work that plan.
> Follow test-driven development for each task: show me the failing run before the fix.
> Do not modify anything under tests/.
> Write a progress.md ledger as you go, and keep it: do not delete the plan
> workspace or its progress.md.
> ```

Keep those last two lines. The skill writes the ledger when each task finishes. It also deletes its own workspace, including the ledger, after its final review is clean ("the git history is the record now"). It did this in one test run. Without the ledger, `superpowers_progress` fails.

Watch two things:

- **A ledger appears**. It gets longer after each task. The ledger is the agent's memory between tasks. It is also your record of its work. The skill chooses its location. Usually it is `.superpowers/sdd/<date>-<feature>/progress.md`. Sometimes it is `progress.md` at the repo root. Both were seen in our test runs. **Leave it where the skill wrote it.** The grader searches both locations. **But the skill git-ignores its own folder.** `.superpowers/sdd/.gitignore` contains `*`. So a plain `git add` does not add the ledger, and it gives no warning. CI never sees the ledger. The commit step below uses `git add -f` for this reason. `check.sh` counts only committed files. It tells you if you missed it.
- **The TDD skill checks every task before it starts.** It checks for a *real* failing run before writing code. Here is a separate trial run. It was a different task. The folder had no `pytest` installed. The skill made the agent stop. The agent did not guess:

> **AGENT OUTPUT — the agent said this. You do not type it.**
>
> ```text
> Blocked before implementation: required test command fails because `pytest` unavailable.
> Strict TDD requires observed behavior failure first, not runner error.
> ```

This is the Week 12 lesson. The agent applies the rule to itself: an `ERROR` is not a red. In your repo, `pytest` is installed. So you should see real red output instead.

**The agent will stop and ask you things.** We saw this in a real run of this lab. Answer each one. Then the agent continues:

| it asks | you answer |
|---|---|
| which execution approach — subagent-driven or native/inline? (end of 2b) | nothing yet. The 2c prompt already names `executing-plans`. That skill is inline |
| “Authorize worktree creation, or permit implementation on `main`?” | `Implement on main. No worktree.` |
| “Implementation complete … merge, open a PR, or keep the branch?” | `Keep the branch as-is.` — then commit yourself, next step |

The execution skill calls two more Superpowers skills itself. They are `using-git-worktrees` and `finishing-a-development-branch`. They are the skills that ask the two questions in the table above.

### 2c-commit. Commit the implementation — separately, and AFTER the test commit

Step 1 told you to commit the tests by themselves. Now commit the agent's work as its own commit:

```console
$ git add app/main.py docs/
$ git add -f .superpowers/sdd/*/progress.md   # the ledger; -f because its folder is git-ignored
$ git commit -m "feat: implement /api/stats"
$ git log --oneline -3
```

If the skill put `progress.md` at the repo root, use `git add progress.md` for the second line. The agent may already commit the implementation. It often does. Look for a `feat:` line after your `test:` line in `git log`. Then commit the ledger on its own: `git add -f .superpowers/sdd/*/progress.md` then `git commit -m "chore: add superpowers ledger"`.

**This is graded.** `red_before_green` saves a copy of your repository at `HEAD` and runs the suite there. Uncommitted work can pass on your laptop and fail in CI. This course tells you not to trust that difference. Two commits, with tests first, are the evidence.

### 2d. Record the evidence — graded

Create **`reports/superpowers.md`** containing:

1. the `codex plugin list` line showing `superpowers` **installed / enabled**
2. the agent's own line naming the **`test-driven-development`** skill
3. a few lines of the session where it ran the suite

This step creates three required checks: `superpowers_used` (the report above), `superpowers_plan` (the dated plan file), and `superpowers_progress` (the ledger). All three are greps. Once the plugin is installed, you never need the network again.

Troubleshooting:

- `codex plugin add` cannot reach the marketplace: use the in-session `/plugins` route. Or install once on any network. After that, it is on disk and works offline.
- **If you really cannot install it at all:** do not stop. Implement `/api/stats` yourself. Finish every other step. Three of the twelve required checks (`superpowers_used`, `superpowers_plan`, `superpowers_progress`) depend on the plugin. A failed install costs those three, not the lab. Record what you tried in `reports/superpowers.md`. Come to Friday's session.
- The plan is saved somewhere else: the skill's path is fixed. Move it to `docs/superpowers/plans/`. Keep the `YYYY-MM-DD-` prefix in the filename.
- No ledger appears anywhere: you asked for `writing-plans` but not `executing-plans`. The ledger belongs to the second skill. Check `.superpowers/` before you decide it is missing.
- The agent edits `tests/`: this is a rule you gave it, not something the tool blocks. Run `git status --porcelain tests/`, `git checkout -- tests/`, then re-prompt with "do not modify anything under tests/".
- The agent writes code without showing a failing run: the skill exists to stop this. Prompt again: "verify the red first and show me the output".
- `501` remains: the route is still the stub. Replace only the endpoint body.
- Percent looks like `0.5` instead of `50.0`: multiply by `100.0`.
- `oracle_reference` fails but your app looks right: you probably rounded. Return the raw float.
- `ZeroDivisionError` on the empty table: guard `total == 0` and return `0.0`.

## Step 3 — Prove green and inspect oracle (20 min)

```console
$ uv run --offline --frozen pytest -q
$ bash check.sh
$ cat results/report.json
```

Every required check must pass for the required score. The stub and each mutant must make your tests fail. The reference and your app must make them pass.

Troubleshooting:

- `oracle_stub` passes: tests likely assert nothing useful.
- `oracle_reference` fails: compare response keys and types against the task contract.
- `red_before_green` fails: your history has no red test commit. Recommit the test before implementation using a new clean attempt.

## Step 4 — Optional challenge (20 min)

Kill extra mutants. Use `os.getenv("STATS_BASE_URL", ...)` with the frozen fixture endpoint. Or make pytest warning-clean under `-W error::DeprecationWarning`. Bonus never changes the required score.

Troubleshooting:

- Bonus says TODO: required work is still valid. Inspect `results/challenge_report.json`.
- Do not use the network. Use frozen fixtures only.
