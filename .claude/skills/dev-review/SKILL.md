---
name: dev-review
description: "Multi-agent code review for specview. Routes to chain-agent (chain layer), spec-backend (Flask/SQLModel), and spec-frontend (Angular) in parallel. Usage: /dev-review"
---

# /dev-review — Code review

Fan out a parallel review across all three domain agents, then synthesize.

## Parameters

- `$ARGUMENTS` — optional path or glob to limit review scope. Defaults to all
  staged/modified files (`git diff --name-only`).

## Procedure

### Step 1 — Gather changed files

```bash
git diff --name-only HEAD
```

Or use `$ARGUMENTS` if provided.

### Step 2 — Classify files by layer

- `api/modules/runtime/chain/**` → chain-agent
- `api/modules/**/routes/**`, `api/modules/**/models.py`, `api/modules/**/services/**` → spec-backend
- `web-ng/src/**` → spec-frontend
- Files spanning multiple layers → all agents

### Step 3 — Fan out (parallel)

Spawn review agents concurrently:
- `chain-agent` reviews chain-layer files.
- `spec-backend` reviews Flask/SQLModel files.
- `spec-frontend` reviews Angular files.

Each agent reads its reference file, then reviews the diff for convention violations.

### Step 4 — Synthesize

Collect all findings. Group by severity:

```
Review: complete
Critical (must fix before merge):
  - api/modules/ai/routes/task_gen.py:42 — Missing @require_auth
  - web-ng/src/app/app.component.ts:88 — setInterval without clearInterval

Warnings (should fix):
  - api/modules/ai/services/epic_guide.py:15 — print() instead of logger

OK: 12 files — no issues
```

## Abort Conditions

- Git is not installed or `git diff` fails.
- No changed files found — report "Nothing to review."

## Allowed Tools

Bash, Read, Glob, Grep, Agent, AskUserQuestion
