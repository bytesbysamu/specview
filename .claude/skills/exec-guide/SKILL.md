---
name: exec-guide
description: "Use this skill when the user wants to execute a task from an implementation guide, implement what the guide describes, or run the implementation plan. Reads implementation-guide.md from a project and dispatches each task to the right specialist agent."
---

# /exec-guide — Implementation Guide Executor

## STOP — Read first

**All steps of the Procedure are mandatory. Steps 5–11 (dev-test, dev-review, fix findings, re-test, commit, PR, report) are not optional — execute them every time, even if the implementation steps went smoothly. Do not report "done" until the PR is opened.**

Read a project's `implementation-guide.md` and execute one or all tasks by
dispatching to the correct specialist agent. The agent reads the task's Steps
and Files sections and makes the actual code changes.

## Parameters

```
/exec-guide <project> [task-N]
```

- `<project>` — project name or path (matched against `data/spec-doc/projects/`)
- `[task-N]` — optional task number to run (e.g. `task-2`). Omit to run all tasks in sequence.

## Pre-flight

1. Resolve project dir: glob `data/projects/*<project>*` and take the first match.
2. Read `implementation-guide.md` from that dir. Abort if missing — run `/impl-guide <project>` first.
3. Parse the task list: find all `## Task N:` headings and their content blocks.
4. If `[task-N]` is given, extract only that task. Otherwise queue all tasks in order.
5. For each task, determine the agent from the **Agent Routing** table below.

## Agent Routing

| Task touches | Dispatch to |
|---|---|
| `api/modules/ai/services/` or `api/modules/ai/workflows/` or `api/modules/ai/prompts/` | `spec-backend` |
| `api/modules/runtime/chain/` or `providers/` | `chain-agent` |
| `web-ng/` or Angular files | `spec-frontend` |
| Multiple layers or cleanup (delete dirs, compose files, test_structural) | `chain-developer` |
| Ambiguous / not clear | `chain-developer` |

## Procedure

For each task to execute:

### 1. Extract task block

Pull the full markdown block for the task — from its `## Task N:` heading to the next `---` or end of file. This becomes the agent's work order.

### 2. Load agent context

Before building the prompt, load the target agent's full definition:

1. Read `.claude/agents/<agent-name>.md` (e.g. `.claude/agents/spec-backend.md`).
2. Parse its **Loaded References** section — find every `plugin/references/*.md` file listed.
3. Read each referenced file from `plugin/references/`.
4. This content becomes the **agent preamble** that leads the subagent prompt.

The goal: the `general-purpose` subagent receives the same persona, quality gates, and conventions that the specialist plugin agent would have loaded in an interactive session.

### 3. Build agent prompt

```
# Agent: <agent-name>

<paste full content of .claude/agents/<agent-name>.md here>

---

# Reference: <reference-file-name>

<paste full content of each plugin/references/*.md listed in the agent's Loaded References>

---

# Task

You are executing Task N from the implementation guide for project "<name>".

Here is the task:

{task_block}

Execute every step listed under "Steps". Make the file changes listed under "Files".
Read files before editing. Run the Verify checks at the end and report results.

Working directory: /Users/sam/Projects/specview
Do not ask for confirmation — execute the steps directly.
```

### 4. Dispatch

Use the Agent tool with `subagent_type: "general-purpose"` and the prompt above.
Run tasks sequentially (each task may depend on the previous).

### 5. Report after each task

```
Task N: <name>
  Status: complete | FAILED
  Files changed: <list>
  Verify: <summary of verify output>
```

### 5. Run tests (automatic — do not skip)

After all tasks complete, invoke the `/dev-test` skill scoped to the nearest relevant module:

Use the Agent tool with `subagent_type: "general-purpose"` and this prompt:
```
Follow the /dev-test skill instructions exactly.
Skill file: /Users/sam/Projects/specview/.claude/skills/dev-test/SKILL.md
Scope: <module path, e.g. modules/ai/routes>
Working directory: /Users/sam/Projects/specview/api
```

If tests fail, stop and report failures. Do not proceed to step 7 until tests pass.

### 7. Run code review (automatic — do not skip)

After tests pass, invoke the `/dev-review` skill on the changed files:

Use the Agent tool with `subagent_type: "general-purpose"` and this prompt:
```
Follow the /dev-review skill instructions exactly.
Skill file: /Users/sam/Projects/specview/.claude/skills/dev-review/SKILL.md
Scope: all files changed in this exec-guide run
Working directory: /Users/sam/Projects/specview
```

Collect the review output and include it in the final summary.

### 8. Fix review findings (automatic — do not skip)

If the review found **critical** findings, fix them before proceeding. Dispatch a `chain-developer` agent with the list of critical findings and the affected files. The agent must:
- Read each affected file
- Apply the fix described in the finding
- Not introduce new issues or change unrelated code

After fixing, re-run dev-test (step 6) to confirm nothing broke. If tests fail, fix and re-test until green.

**Warnings** are logged in the summary but do not block the PR. Do not fix warnings unless they are trivial one-line changes.

### 9. Commit all changes

Stage all changed and new files from the exec-guide run and commit:

```bash
git add <all changed files>
git commit -m "<type>: <description>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Use `feat:` for new features, `fix:` for bug fixes, `refactor:` for refactors. The commit message should summarize what the epic delivered, not list individual tasks.

### 10. Open PR

Push the branch and open a PR against `master`:

```bash
git push -u origin <current-branch>
gh pr create --title "<short title>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points summarizing what this PR delivers>

## Tasks completed
<list of tasks from the implementation guide>

## Test plan
- [ ] Backend tests pass (modules/auth)
- [ ] Frontend builds cleanly
- [ ] Manual: verify signup flow end-to-end
- [ ] Manual: verify token refresh works
- <any task-specific manual checks>

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 11. Write summary file and report

Write the following to `data/projects/<project-dir>/exec-guide-summary.md` using the Write tool:

```markdown
# exec-guide summary — <project name>

**Date:** <today's date>
**Tasks run:** N
**Tasks passed:** N / N
**Tests:** passed | FAILED (backend: <module> — N passed)
**Review:** <initial critical count> critical (all fixed), <warning count> warnings
**PR:** <PR URL>

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: <name> | ✓ complete | file1.py, file2.py |
| Task 2: <name> | ✓ complete | file3.py |

## Test results

<paste dev-test output summary>

## Review findings

### Fixed (critical)
<list of critical findings that were fixed>

### Acknowledged (warnings)
<list of warnings, or "No warnings">

## Next steps

- Review and merge PR: <PR URL>
- <any manual follow-ups noted by agents>
```

Then print the final report to the conversation:

```
exec-guide: complete
  Tasks run: N  (N passed, 0 failed)
  Tests: passed (backend: <module> — N passed)
  Review: N critical (fixed), N warnings (acknowledged)
  PR: <PR URL>
  Summary: data/projects/<project-dir>/exec-guide-summary.md
```

## Abort Conditions

- `implementation-guide.md` not found → stop, tell user to run `/impl-guide <project>` first.
- Agent reports a blocking error on a task → stop, report the error, do not proceed to the next task.
- A Verify check fails → treat as a blocking error; report and stop.
- Tests fail after implementation → stop, report failures, do not run review, do not write summary file.
- Tests fail after fixing review findings → stop, report failures.

## Notes

- Always run tasks in order — later tasks depend on earlier ones.
- The agent has full tool access and will read, edit, and run tests itself.
- dev-test and dev-review are always invoked automatically — never skip them.
- Critical review findings are always fixed before committing.
- The skill commits, pushes, and opens a PR — the pipeline ends with a reviewable PR.

## Allowed Tools

Agent, Read, Glob, Grep, Bash
