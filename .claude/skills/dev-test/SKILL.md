---
name: dev-test
description: "Use this skill when the user asks to run tests, check if tests pass, verify a fix with tests, mentions failing tests, or wants to confirm nothing is broken after a change. Also use after implementing any new feature or bug fix."
---

# /dev-test — Run tests

Run the test suite for the detected stack, scoped to the nearest module.

## STOP — Read first

Never skip failing tests. Never use `--ignore` to hide failures. Report all failures.

## Stack Detection

Same rules as `/dev-build` — detect from cwd.

## Procedure

### Backend — specific module

If cwd is inside `api/modules/{name}/`:

```bash
cd /path/to/specview/api
python -m pytest modules/{name}/ -v 2>&1
```

### Backend — full suite

```bash
cd /path/to/specview/api
python -m pytest -v 2>&1
```

### Frontend

```bash
cd /path/to/specview/web-ng
npx ng test --watch=false --browsers=ChromeHeadless 2>&1
```

## Output Format

**Success:**
```
Tests: passed (backend: modules/ai — 14 passed)
```

**Failure:**
```
Tests: FAILED (backend: modules/ai)
Failures:
  - test_epic_guide.py::test_start — AssertionError: expected 200, got 403
  - test_epic_guide.py::test_poll — KeyError: 'done'
```

## Allowed Tools

Bash, Read, Glob, Grep
