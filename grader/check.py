"""Offline grader. Student tests are executed unchanged against owned variants."""

import re
import ast
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient


def hint(*args):
    """Diagnostic detail. Off by default: the lab reports PASS/FAIL only, like the
    pre-midterm labs. Set W12_HINTS=1 to see why a check failed."""
    if os.environ.get("W12_HINTS"):
        print(*args)

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests" / "test_stats.py"


def run(command, cwd=ROOT, env=None):
    return subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def tracked(path):
    """True when git tracks `path`. CI grades a fresh checkout, so an untracked or
    git-ignored file that passes locally is simply absent in CI - count only what
    was committed, so the local score and the CI score agree."""
    return run(["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))]).returncode == 0


def assertion_failure(result):
    output = result.stdout
    errored = "ERROR collecting" in output or "ImportError" in output or "ModuleNotFoundError" in output
    return result.returncode != 0 and "AssertionError" in output and not errored


def baseline_green():
    return run(["uv", "run", "--offline", "--frozen", "pytest", "-q", "tests/test_app.py"]).returncode == 0


def student_tests_exist():
    if not TEST.is_file():
        return False
    try:
        tree = ast.parse(TEST.read_text())
    except SyntaxError:
        return False
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
    source = TEST.read_text()
    # accept either quote style: get("/api/stats") and get('/api/stats')
    calls = len(re.findall(r"""get\(\s*['"]/api/stats['"]""", source))
    return len(functions) >= 3 and calls >= 3


def variant_result(name):
    """Run the student's tests against a variant built from their OWN app.

    No corrected implementation ships with this template: a variant is the
    student's app with the /api/stats response perturbed at request time by
    grader/variant_conftest.py. See that file for why.
    """
    if not TEST.is_file():
        return False, "tests/test_stats.py missing"
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        shutil.copytree(ROOT / "app", workspace / "app")
        shutil.copytree(ROOT / "tests", workspace / "tests")
        shutil.copy2(ROOT / "grader" / "variant_conftest.py", workspace / "conftest.py")
        (workspace / "data").mkdir(exist_ok=True)
        environment = dict(os.environ, W12_VARIANT=name, PYTHONPATH=str(workspace))
        result = run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--rootdir", str(workspace),
             str(workspace / "tests" / "test_stats.py")],
            cwd=workspace, env=environment,
        )
    if "ERROR collecting" in result.stdout or "ImportError" in result.stdout or "ModuleNotFoundError" in result.stdout:
        return False, "student test errored instead of asserting"
    return result, result.stdout


def oracle(name, should_pass):
    outcome, detail = variant_result(name)
    if isinstance(outcome, bool):
        return False, detail
    ok = outcome.returncode == 0 if should_pass else assertion_failure(outcome)
    return ok, "pass" if ok else ("expected assertion failure" if not should_pass else "expected passing tests")


def red_before_green():
    commits = run(["git", "log", "--format=%H", "--", "tests/test_stats.py"]).stdout.splitlines()
    if not commits:
        return False, "commit tests/test_stats.py before implementation"
    first = commits[-1]
    with tempfile.TemporaryDirectory() as temp:
        archive = subprocess.run(["git", "archive", first], cwd=ROOT, stdout=subprocess.PIPE)
        with tarfile.open(fileobj=__import__("io").BytesIO(archive.stdout)) as bundle:
            bundle.extractall(temp, filter="data")
        checkout = Path(temp)
        result = run([sys.executable, "-m", "pytest", "-q", "tests/test_stats.py"], cwd=checkout)
    if not assertion_failure(result):
        return False, "first test commit must fail on an assertion; commit test before implementation"
    # Evaluate the COMMITTED state, not the working tree. A student who never commits
    # the implementation would otherwise score green here and red in CI, which is the
    # exact divergence this course tells them to distrust (verified 2026-09-28).
    with tempfile.TemporaryDirectory() as temp:
        archive = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, stdout=subprocess.PIPE)
        with tarfile.open(fileobj=__import__("io").BytesIO(archive.stdout)) as bundle:
            bundle.extractall(temp, filter="data")
        head = run([sys.executable, "-m", "pytest", "-q", "tests/test_stats.py"], cwd=Path(temp))
    if head.returncode != 0:
        return (False, "commit your implementation: at HEAD the suite must pass "
                       "(uncommitted work passes locally but fails in CI)")
    return (True, "head must pass after implementation")


def app_green():
    """Assert the /api/stats contract ourselves, independently of the student's tests.

    This is the grader's own opinion about correctness, and it carries the
    rounding-sensitive case on purpose. `oracle_reference` runs the student's
    tests against the student's own app, so it cannot by itself catch an
    implementation that is wrong in a way the student's tests happen to agree
    with. The seeded case (2 of 4 -> 50.0) is a whole number and would let a
    round() implementation through; 2 of 7 does not.
    """
    import sqlite3
    import tempfile
    from pathlib import Path as _Path

    try:
        from app.main import app, ensure_database
        import app.main as student_main

        ensure_database()
        with tempfile.TemporaryDirectory() as temp:
            target = _Path(temp) / "app.db"
            with sqlite3.connect(student_main.DB_PATH) as source, sqlite3.connect(target) as copy:
                source.backup(copy)
            original = student_main.DB_PATH
            student_main.DB_PATH = target
            try:
                client = TestClient(app)
                seeded = client.get("/api/stats")
                if seeded.status_code != 200:
                    return False
                if seeded.json() != {"total": 4, "done": 2, "percent_done": 50.0}:
                    return False

                for index in range(3):
                    created = client.post(
                        "/cards", params={"title": f"grader {index}", "status": "todo"}
                    )
                    if created.status_code != 201:
                        return False

                uneven = client.get("/api/stats")
                if uneven.status_code != 200:
                    return False
                body = uneven.json()
                expected = 100.0 * 2 / 7
                return (
                    body.get("total") == 7
                    and body.get("done") == 2
                    and isinstance(body.get("percent_done"), float)
                    and abs(body["percent_done"] - expected) < 1e-12
                )
            finally:
                student_main.DB_PATH = original
    except Exception as error:
        hint(error)
        return False


def agents_md():
    path = ROOT / "AGENTS.md"
    return path.is_file() and "Testing rules" in path.read_text() and "Do not edit `tests/`" in path.read_text()


def superpowers_used():
    """Evidence that the Superpowers TDD skill drove the implementation.

    Required. The student installs the plugin, works the red-green loop through it,
    and commits the evidence. Checked offline by grepping their own report, so a
    student with no network after setup can still satisfy it.
    """
    path = ROOT / "reports" / "superpowers.md"
    if not path.is_file():
        hint("missing reports/superpowers.md - see TASKS.md Step 2")
        return False
    text = path.read_text().lower()
    missing = []
    if "superpowers" not in text:
        missing.append("the plugin name")
    if not any(word in text for word in ("installed", "enabled")):
        missing.append("a `codex plugin list` line showing it installed/enabled")
    if "test-driven-development" not in text:
        missing.append("the skill name test-driven-development as the agent announced it")
    if missing:
        hint("reports/superpowers.md is missing: " + "; ".join(missing))
        return False
    return True


def superpowers_plan():
    """The writing-plans skill must have produced a real plan document.

    The skill saves to a deterministic path, docs/superpowers/plans/YYYY-MM-DD-<name>.md,
    and its template fixes the header. Both are greppable offline.
    """
    plans = sorted((ROOT / "docs" / "superpowers" / "plans").glob("*.md")) \
        if (ROOT / "docs" / "superpowers" / "plans").is_dir() else []
    if not plans:
        hint("no plan under docs/superpowers/plans/ - see TASKS.md Step 2b")
        return False
    untracked = [p for p in plans if not tracked(p)]
    plans = [p for p in plans if tracked(p)]
    if not plans:
        hint("the plan exists but is not committed - CI only sees committed files: "
              "git add " + " ".join(str(p.relative_to(ROOT)) for p in untracked))
        return False
    dated = [p for p in plans if re.match(r"\d{4}-\d{2}-\d{2}-", p.name)]
    if not dated:
        hint("plan filename must start YYYY-MM-DD- as the skill writes it; found: "
              + ", ".join(p.name for p in plans))
        return False
    text = "\n".join(p.read_text() for p in dated).lower()
    missing = [k for k in ("goal:", "task") if k not in text]
    if missing:
        hint("plan is missing the skill's header sections: " + ", ".join(missing))
        return False
    return True


def superpowers_progress():
    """The execution skill keeps a ledger as it works the plan.

    Path verified against a real run (2026-09-27): the ledger landed at
    .superpowers/sdd/<date>-<feature>/progress.md, NOT the repository root, so search
    for it rather than assuming one location. Skipping .venv keeps pytest's own
    terminalprogress.py out of the match.
    """
    found = [p for p in ROOT.rglob("progress.md")
             if ".venv" not in p.parts and "node_modules" not in p.parts
             and not p.name.endswith(".bak")]
    untracked = [p for p in found if not tracked(p)]
    found = [p for p in found if tracked(p)]
    if untracked and not found:
        hint("the ledger exists but is not committed, so CI cannot see it. Its folder is "
              "git-ignored by the skill; commit it with: git add -f "
              + " ".join(str(p.relative_to(ROOT)) for p in untracked) + " (see TASKS.md Step 2c)")
        return False
    if not found:
        hint("no progress.md ledger found - the execution skill writes one as it works "
              "the plan (commonly .superpowers/sdd/<date>-<feature>/progress.md); "
              "see TASKS.md Step 2c")
        return False
    text = "\n".join(p.read_text() for p in found).lower()
    if "task" not in text:
        hint("the ledger has no task entries - it should record each task as it finishes")
        return False
    return True


def extra_mutants():
    return all(oracle(name, False)[0] for name in ("mutant_c", "mutant_d"))


def injected_contract():
    return "STATS_BASE_URL" in TEST.read_text() if TEST.exists() else False


def warnings_clean():
    return run(["uv", "run", "--offline", "--frozen", "pytest", "-q", "-W", "error::DeprecationWarning"]).returncode == 0


CHECKS = {
    "baseline_green": baseline_green,
    "student_tests_exist": student_tests_exist,
    "oracle_stub": lambda: oracle("stub", False)[0],
    "oracle_reference": lambda: oracle("reference", True)[0],
    "oracle_mutant_a": lambda: oracle("mutant_a", False)[0],
    "oracle_mutant_b": lambda: oracle("mutant_b", False)[0],
    "red_before_green": lambda: red_before_green()[0],
    "app_green": app_green,
    "agents_md": agents_md,
    "superpowers_used": superpowers_used,
    "superpowers_plan": superpowers_plan,
    "superpowers_progress": superpowers_progress,
    "extra_mutants": extra_mutants,
    "injected_contract": injected_contract,
    "warnings_clean": warnings_clean,
}

if __name__ == "__main__":
    name = sys.argv[1]
    try:
        sys.exit(0 if CHECKS[name]() else 1)
    except Exception as error:
        hint(error)
        sys.exit(1)
