# Quality Gates — spec-doc Implementation Guides

Rules enforced by `modules/quality/lint.lint_task_guide()`. Your output is checked against these before the file is written.

## Structure Rules
- Every task guide must start with `# Task N` (where N matches the task number)
- Required sections: `## Overview`, `## Prerequisites`, `## Implementation Steps`, `## Tests`, `## Verification`
- No section may be empty
- Cross-references to other task guides use relative paths: `[Task 1.1](./task-1.1-name.md)`

## Implementation Step Rules
- Every step has a numbered header: `### Step N: <verb> <noun>`
- Every new file reference is marked `(new)` inline
- Every test has a complete assertion body (no `assert True` or `# TODO`)
- Every path is real (exists in the codebase) or explicitly marked `(new)`
- No placeholder values like `YOUR_VALUE`, `<INSERT>`, `TODO`

## Content Routing Rules (from bootstrap prompts)
- Status words (Done, In Progress, Completed) → ONLY in timeline.md, never in task guides
- Code blocks with implementation → task guides ONLY (not in epic/architecture)
- Business value, market analysis → ONLY in epic.md
- Design decisions, tech stack → ONLY in architecture.md
- Problem identification → ONLY in analysis.md

## Code Quality Rules
- max-line-length = 120
- No `str | None` syntax in generated Python — use `Optional[str]`
- No unused imports
- Daemon threads only (`daemon=True`)
- No `except Exception: pass` — always log or re-raise

## Co-Authorship
Every task guide ends with:
```
---
Co-Authored-By: <model display name> <noreply@anthropic.com>
```
The executor attribution is injected automatically by `build_implementation_guide_prompt()`.
