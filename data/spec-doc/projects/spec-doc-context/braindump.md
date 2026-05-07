# Spec-Doc Context Layer — Braindump

## What it is

Six markdown files at the root of `~/Projects/2026/spec-doc/` that function as the shared context layer injected into every AI task generation call. These are not code — they are structured prose that the spec-doc system reads, combines via `PromptBuilder`, and passes as system context to the AI chain. Together they define who is building, what environment they're targeting, what rules are non-negotiable, what quality gates exist, what patterns to reuse, and what version pins to use.

The six files:

| File | Role |
|------|------|
| `builder.md` | Sam's role, active projects, stack preferences, known constraints |
| `codebase.md` | Target environment: OpenClaw workspace layout, container mounts, URL table |
| `principles.md` | 7 non-negotiable engineering rules (P1–P7) |
| `quality.md` | Lint rules enforced on generated task guides |
| `references.md` | Real working patterns from sibling projects to port from |
| `versions.md` | Pinned runtime/library/model versions injected into every guide |

## Problem it solves

Without this layer, every AI-generated spec or task guide would be generic. The context layer grounds generation in Sam's actual stack, constraints, and live environment so guides are runnable without manual correction. It's the difference between "here's a generic Flask route" and "here's the exact pattern that works in this repo, at this port, for this deployment target."

## Current state

All six files are actively maintained and in use. The spec-doc API's `modules/context/service.py` reads them via `read_context()`. `PromptBuilder.section()` skips any empty file gracefully. The files are under active revision as the system evolves (e.g., `codebase.md` reflects the OpenClaw workspace as it currently exists; `versions.md` tracks Angular 17, Flask 3.x, claude-sonnet-4-6, etc.).

## Key decisions already made

- **Six separate files, not one blob**: Each file has one job — avoids context window bloat when only one section is needed; enables per-endpoint context injection.
- **`principles.md` is non-negotiable**: The analysis step is explicitly supposed to flag when a brain dump contradicts a principle, not silently ignore it. This is an enforcement mechanism, not just reference.
- **`references.md` describes patterns, not implementations**: Points at real sibling-project files (`modules/chain/adapter.py`, `~/Projects/financing-plugin-extracted/`) — agents read from there, not from inline duplicates.
- **`versions.md` is injected into every guide**: Version pins (Python 3.11, datamodel-codegen 0.45.0, pydantic 2.x, etc.) are explicit so generated code doesn't drift.
- **`quality.md` is machine-enforced**: The lint rules in `quality.md` map directly to `modules/quality/lint.lint_task_guide()` — generated guides that violate them are rejected before being written.

## Open questions

- **Staleness risk**: `codebase.md` describes the OpenClaw workspace as it is now. Skills listed as `[TO BUILD]` (`sam-context`, `sam-specDoc`, `sam-projects`) — when they ship, `codebase.md` needs updating.
- **`versions.md` says Angular 17, but `builder.md` says Angular 17 (standalone, signals)**:  actual Angular version in Bubls vs spec-doc vs ionstarter may differ — version pins need per-project overrides eventually.
- **`principles.md` P3 (Async 202 + Polling)** isn't enforced by lint yet — it's a prose rule. Should be added to `quality.md` as a structural check on task guides for long-running operations.
- **Who updates these files?**: Currently manual. As the system matures, context files could be auto-updated by a SessionStart hook or a dedicated "refresh context" skill.

## Next steps

- Update `codebase.md` each time the OpenClaw workspace evolves (new skills graduating, port changes).
- Add `versions.md` overrides mechanism for per-project version divergence.
- Promote P3 from principles prose to a quality gate in `quality.md`.
- Consider a `sam-context` skill that reads these files and generates a session snapshot automatically on boot.
