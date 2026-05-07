---
name: exec-guide
description: "Use this skill when the user wants to execute a task from an implementation guide, implement what the guide describes, or run the implementation plan. Reads implementation-guide.md from a project and dispatches each task to the right specialist agent."
---

# /exec-guide — Implementation Guide Executor

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

### 2. Build agent prompt

```
You are executing Task N from the implementation guide for project "<name>".

Here is the task:

{task_block}

Execute every step listed under "Steps". Make the file changes listed under "Files".
Read files before editing. Run the Verify checks at the end and report results.

Working directory: /Users/sam/Projects/specview
Do not ask for confirmation — execute the steps directly.
```

### 3. Dispatch

Use the Agent tool with the correct `subagent_type` and the prompt above.
Run tasks sequentially (each task may depend on the previous).

### 4. Report after each task

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

If tests fail, stop and report failures. Do not proceed to step 6 until tests pass.

### 6. Run code review (automatic — do not skip)

After tests pass, invoke the `/dev-review` skill on the changed files:

Use the Agent tool with `subagent_type: "general-purpose"` and this prompt:
```
Follow the /dev-review skill instructions exactly.
Skill file: /Users/sam/Projects/specview/.claude/skills/dev-review/SKILL.md
Scope: all files changed in this exec-guide run
Working directory: /Users/sam/Projects/specview
```

Collect the review output and include it in the final summary.

### 7. Final summary

```
exec-guide: complete
  Tasks run: N
  Tasks passed: N
  Tasks failed: 0
  Tests: passed (backend: <module> — N passed)
  Review: <critical count> critical, <warning count> warnings
  Next: run /commit to commit the changes
```

## Abort Conditions

- `implementation-guide.md` not found → stop, tell user to run `/impl-guide <project>` first.
- Agent reports a blocking error on a task → stop, report the error, do not proceed to the next task.
- A Verify check fails → treat as a blocking error; report and stop.
- Tests fail after implementation → stop, report failures, do not run review.

## Notes

- Always run tasks in order — later tasks depend on earlier ones.
- The agent has full tool access and will read, edit, and run tests itself.
- dev-test and dev-review are always invoked automatically — never skip them.
- This skill does not commit — run `/commit` after reviewing the output.

## Allowed Tools

Agent, Read, Glob, Grep, Bash
