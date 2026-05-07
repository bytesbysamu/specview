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

### 5. After all tasks

```
exec-guide: complete
  Tasks run: N
  Tasks passed: N
  Tasks failed: 0
  Run /dev-test to confirm the full test suite.
```

## Abort Conditions

- `implementation-guide.md` not found → stop, tell user to run `/impl-guide <project>` first.
- Agent reports a blocking error on a task → stop, report the error, do not proceed to the next task.
- A Verify check fails → treat as a blocking error; report and stop.

## Notes

- Always run tasks in order — later tasks depend on earlier ones.
- The agent has full tool access and will read, edit, and run tests itself.
- If a task says "Delete `path/to/file`", the agent will delete it.
- If a task says "run `pytest`", the agent will run it and check results.
- This skill does not commit — run `/commit` after reviewing the changes.

## Allowed Tools

Agent, Read, Glob, Grep, Bash
