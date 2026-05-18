---
name: Task-exec workflow must be mechanical
description: When user says "do task X" — assemble executor/guide prompts from epic + architecture + context blocks. Never hand-write prompts.
type: feedback
originSessionId: bceb2169-d048-4238-ac89-4934b0936057
---
Task-exec prompts must be assembled mechanically from spec docs, never improvised.

**Why:** Hand-written executor prompts drift from the spec docs (e.g., epic was corrected but architecture wasn't, causing conflicting data for the executor). The spec docs should be the single source of truth.

**How to apply:** When user says "do task X" (or "run task-exec on task X"):

1. Identify project dir from context (e.g., `projects/checkin-ionstarter/`)
2. Read `epic.md` → extract the Task X description (parse by `#### Task N:` headers)
3. Read `architecture.md` → extract the Task X component design section
4. Load context blocks: `builder.md` + `principles.md` from spec-doc (`/projects/2026/spec-doc/`)
5. Read the ionstarter reference domain code (`domains/tasks/`) for pattern grounding
6. Assemble Agent G prompt from template → launch guide agent FIRST
7. When guide is done → push .v2.md to sidebar immediately
8. Assemble Agent E prompt with the GUIDE as primary input → executor follows the guide, doesn't rediscover patterns
   - This is sequential (guide then executor) but saves tokens and produces more consistent output
   - The guide IS the implementation spec; executor just follows it
   - Executor MUST commit after implementation (Phase 5). Current agents skip this — fix the prompt to enforce it.
   - Executor must set git config (user.email/user.name) before committing if not configured.
   - Each task gets its own commit with conventional-commit message + Co-Authored-By line.
9. On completion: verify build, diff guide vs executor
10. Push .v2.md guide(s) to the spec-doc sidebar project (PUT to existing project, same as epic lives in)
11. Write .v2.md files to the local `projects/{name}/` directory alongside epic.md

**The .v2.md guides are part of the project spec docs** — they live in the same folder as epic.md/architecture.md and get pushed to the same spec-doc sidebar project. Push to sidebar IMMEDIATELY when the guide agent finishes — don't wait for the executor. The user expects to see it in the sidebar the moment it's ready.

Never compose executor prompts by hand. If the epic/architecture is wrong, fix THOSE first, then run task-exec.
