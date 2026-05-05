---
sidebar_position: 1
---

# 🔍 Text Chains — Analysis

**Purpose**: Surface constraints, open questions, and dependencies before scoping the epic.

**Date**: 2026-04-16

---

## Problem

Bubls' /text page runs single-shot Claude calls through the chain adapter. Users get one rewrite per tap. Humanize-me proved that 3-pass chaining produces dramatically better humanization than single-shot — that quality gap is the entire product moat ($195K MRR validated by StealthGPT). Spec-doc proved that context-injected multi-file generation works: 6 task specs generated in one session, each consuming builder + principles + references + prior-task output. Neither pattern is available to Bubls users today. The infrastructure is live (chain adapter shipped in Epic 2 Task 2, /text route in Epic 2 Task 7, builder profile on user model) but only runs one call at a time through it.

## Hard Constraints

- **Chain adapter is the only Claude boundary** — no direct provider imports anywhere in feature code (Epic 2 invariant, enforced by structural test)
- **Context files live in-repo** — not user-editable for v1 (braindump decision: "code-in-repo not editable-in-app")
- **Single-shot modes stay untouched** — additive only, zero regressions on existing Rewrite/Expand/Compress/Clarify/Generate
- **OpenAPI YAML is source of truth** — new `POST /api/text/chain` endpoint must be spec'd there first, DTOs regenerated both sides
- **Always ORM, never raw SQL** — generation persistence through SQLAlchemy on existing `superapp_generations`
- **Feature-gated per user** — `enabled_features.text_chains` flag; null-object fallback on frontend (locked, not hidden)

## Open Questions (resolved)

| Question | Resolution | Rationale |
|---|---|---|
| Which chains ship first? | Both deep-humanize AND braindump-to-docs, plus rewrite-review. | Humanize validates the pipeline (proven code, direct port from humanize-me). Braindump differentiates (nobody else has multi-file text generation). Rewrite-review rounds out the set cheaply (2 existing ops composed). |
| Context block shape? | Flat markdown files + manifest.json. | Manifest maps block names → file paths. Human-readable, git-diffable, same shape as spec-doc's `builder.md`/`principles.md`. Structured YAML rejected (no tooling benefit). DB blobs rejected (not versionable). |
| Pricing impact? | Bundled into existing plans for v1. | Chain ops cost 3–5x tokens. Track usage via existing `superapp_generations` table. Gate later when pricing tiers diverge per chain. Future shape named now: `enabled_features.chain:{chainId}` — but don't build the resolver until the second tier exists. |
| Multi-file output UI? | Tabs within existing output area. | Each tab = one generated file. Copy-per-tab button. No new route. Accordion rejected (harder to scan). Downloadable zip rejected (loses in-app preview). |
| Streaming or request-response? | Request-response for v1. | Matches existing `/api/ai/text/rewrite` pattern. SSE per chain step deferred — trigger: when chains exceed 30s and users report perceived hangs. |
| Step handler dispatch? | `STEP_HANDLERS: dict[str, Callable]` dispatch map. | Adding a new operation = one function + one dict entry. No if/elif branches in the runner loop. Extensible without touching the core loop. |

## Dependencies

| Dependency | Status | Location |
|---|---|---|
| Chain adapter (Epic 2, Task 2) | Shipped | `server/modules/chain/adapter.py` |
| /text route + TextApiService (Epic 2, Task 7) | Shipped | `server.js` lines 617–650, `src/app/services/ai.service.ts` |
| Builder profile on user model (Epic 2, Task 1) | Shipped | `builder.md` loaded at server startup |
| `superapp_generations` table (Epic 2, Task 7) | Shipped | SQLAlchemy model, `feature` column exists |
| OperationBarComponent (shipped) | Shipped | `src/app/components/operation-bar/operation-bar.component.ts` |
| Architecture principles file | Shipped | `principles.md` loaded at server startup |

## Explicitly Out of Scope

- User-editable context blocks (v2 — needs settings page + versioning + security review for prompt injection)
- SSE/streaming for chain steps (v2 — request-response is sufficient until chains exceed 30s)
- Chain composition UI where users pick steps (ship fixed chains, iterate from usage data)
- Cost analytics dashboard (track usage now, surface later when there's enough data)
- Offline chain execution
- Changes to the existing 5 single-shot rewrite modes

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

