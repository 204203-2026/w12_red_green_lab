# w12_red_green_lab

Week 12: **TDD with Superpowers** — you write the tests, the
[Superpowers](https://github.com/obra/superpowers) skills plugin writes the endpoint.

This week's subject is the plugin. Test-driven development is the background that makes
its behaviour readable: it plans the work, then refuses to write code until a test for
that code is already failing. Three of the twelve required checks are evidence that you
drove it — the plan it wrote, the ledger it kept, and your own red and green commits.

```console
$ bash init.sh      # set up, seed the database
$ bash check.sh     # your score, offline and deterministic
```

Then read `TASKS.md`. Required grading is offline; no Docker, no network after setup.

**The split:** `tests/test_stats.py` is yours, written from the contract before the
endpoint exists and locked once committed. `/api/stats` in `app/main.py` is written by
Codex, driven by Superpowers. Your grade rests on whether your tests can tell a correct
implementation from a broken one.
