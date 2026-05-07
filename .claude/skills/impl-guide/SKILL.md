---
name: impl-guide
description: "Use this skill when the user wants to generate a high-level implementation guide for a project's epic — a single executable document covering all tasks, no code, fast to generate. Takes epic.md and architecture.md as input."
---

# /impl-guide — Implementation Guide Generator

Generate a single, executor-ready implementation guide covering every task in the epic.
High-level. No code. Fast. Architecture and epic are the only inputs.

## Parameters

- `$ARGUMENTS` — project directory path, or project name (partial match against `data/spec-doc/projects/`)

## Pre-flight

1. Resolve project dir. If `$ARGUMENTS` looks like a path, use it directly. Otherwise glob `data/spec-doc/projects/*$ARGUMENTS*` and take the first match.
2. Read `epic.md` from the project dir. Abort if missing.
3. Read `architecture.md` from the project dir. Abort if missing.
4. `analysis.md` is optional — include if present.

## Prompt

Construct the prompt as follows. Do NOT add sections beyond what is listed.

### System

```
You are a senior engineer producing a high-level implementation guide.
Your output is a planning document for a developer who already understands the codebase.
No code. No test bodies. No rollback scripts. Pure prose and file lists.
```

### User

```
## Your ONE Job
Produce a single implementation-guide.md covering every task in the epic.
Each task gets its own section. The document opens with a shared context block.

## Required Structure (follow exactly)

# Implementation Guide: {epic title}

## Overview
One paragraph: what this epic delivers and how tasks sequence.

## Shared Pre-flight
Bullet list of setup steps that apply across all tasks (env vars, flags, migrations).
No more than 8 bullets.

---

## Task {N}: {Name}  [Effort: {X}]

### What
One to three sentences: what this task accomplishes and why.

### Files
- **Create**: `path/to/new-file.py` — one-line description
- **Modify**: `path/to/existing.py` — what changes and why

### Steps
Numbered prose steps. No code. Each step is one to two sentences.
Reference file paths and function names, but do not write their bodies.

### Verify
Two to four bullet points: how to confirm the task is done correctly.
Shell commands are allowed here (e.g. `pytest`, `curl`). No code logic.

---

## Task {N+1}: {Name}  [Effort: {X}]
...

## Hard Rules
- Response MUST begin with `#`. No preamble, no "Here is the guide".
- NO code blocks (no ``` fences with implementation code).
- NO empty placeholders: `<TBD>`, `path/to/whatever`, `TODO`. Use real paths.
- NO absolute personal paths (`/Users/...`). Use workspace-relative paths.
- Cover EVERY task listed in the epic. Do not skip any.
- Shared pre-flight goes in the header section only — do not repeat per task.
- Keep each task section tight: what + files + steps + verify. Nothing else.

## EPIC
{epic_content}

## ARCHITECTURE
{arch_content}

{analysis_section}

Generate the implementation guide now.
```

## Procedure

1. Read the three files (epic, architecture, optional analysis).
2. Substitute content into the prompt template above.
3. Call the chain: `chain.generate(system, user, model="claude-sonnet-4-6", max_tokens=8192)`
   - If running as a plugin skill (no API): use `claude -p "<user prompt>" --system "<system>"` directly.
4. Write output to `{project_dir}/implementation-guide.md`.
5. Report:

```
impl-guide: complete
  ✦ implementation-guide.md  written ({size} kB)
  Tasks covered: {N}
```

## Abort Conditions

- `epic.md` missing → stop, report.
- `architecture.md` missing → stop, report.
- Output does not begin with `#` → regenerate once; if still wrong, stop and report raw output.

## Notes on Speed

- Use `claude-sonnet-4-6`, not opus — this is a planning doc, not a code doc.
- Do NOT inject builder/principles/codebase/references context — those are for code generation.
  Architecture already encodes the relevant conventions. Extra context slows the model and adds noise.
- If the epic has more than 8 tasks, split into two `generate()` calls: tasks 1–N/2 and N/2+1–N,
  then concatenate with a `---` separator. Announce the split to the user.

## Allowed Tools

Bash, Read, Glob, Grep, Write
