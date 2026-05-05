# 🔍 V2 Spec Doc Backend — Analysis

## The Problem
server.js is a 1,651-line monolith that grows with every feature. The Bubls backend proved a modular Flask pattern (7 modules, 164 tests, zero regressions). Porting spec-doc to the same pattern lets both products share AI infrastructure and makes new features a folder instead of more lines.

## Hard Constraints
- Zero Angular frontend changes — backend is a drop-in replacement
- Filesystem-only persistence — no database, no auth (single-user tool)
- Flask backend — matches Bubls pattern and builder's primary stack
- Existing 64 projects in `projects/` must load without migration scripts
- Claude CLI must be installed for AI operations (Phase 2, but chain module assumes it)

## Open Questions
- **Port during migration**: Same port (3100) forces a hard cutover. Different port means parallel running but requires a one-time frontend config change at switchover. Which?
- **Code sharing strategy**: Brain dump says "bug fixes flow both ways" — is this copy-paste-and-drift, a shared Git submodule, or a published package? This determines how much Phase 1 adaptation is safe.
- **Projects folder compatibility**: Do the 64 existing project directories work as-is with the new Flask file routes, or do path conventions differ (trailing slashes, encoding, nested structure)?

## Dependencies & Sequencing
- Flask app factory + Blueprint registration must land before any module work — it's the skeleton everything mounts to.
- Project CRUD endpoints and context file endpoints are independent of each other — can run in parallel.
- Chain module has zero dependents in Phase 1 — it can land anytime before Phase 2 starts, including *during* Phase 2.
- Port decision must be made before frontend cutover, but doesn't block backend development (develop on any port, decide at integration time).

## Explicitly Out of Scope
- **Chain module in Phase 1** — the adapter, three providers, file marker parser, and context block loader have NO consumer until Phase 2 wires up AI endpoints. Builder principle: "Ship the car, not the engine — no infrastructure before first user." Porting it now is speculative infrastructure. **Defer to Phase 2 start.** Re-scope if Phase 1 surfaces a need for any chain component (it won't — CRUD is pure filesystem).
- **Walker.py** — brain dump already calls this out. No consumer until scan endpoint (Phase 2).
- **Shared package extraction** — "bug fixes flow both ways" implies a package, but extracting one is a separate scope. Copy-paste is fine for Phase 1. Re-scope when the second divergence bug proves the cost of drift.
- **SSE streaming, container management, database, auth** — brain dump already excludes these. Agreed.