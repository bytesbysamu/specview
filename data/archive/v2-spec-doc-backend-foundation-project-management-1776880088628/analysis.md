# 🔍 V2 Spec Doc Backend — Foundation + Project Management — Analysis

## The Problem

`server.js` is 1,651 lines with no module boundaries — every new feature grows the file. The Bubls backend solved this with a modular Flask pattern (7 modules, 164 tests, zero regressions). Porting spec-doc to the same pattern lets Phase 2 AI operations land on verified infrastructure instead of untested plumbing.

## Hard Constraints

- API contract must be byte-identical to Express — zero Angular changes is a hard requirement, not a preference
- Filesystem only — no DB, no auth; 64 existing `projects/` directories must load without migration
- Flask only — builder profile confirms "Python (Flask) for product APIs, Express for tooling"
- Bubls chain module is the source copy — do not re-architect it during the port

## Open Questions

- **Port strategy**: Flask on 3100 (Express must vacate) vs. a different port (frontend needs a one-line env swap at cutover). Success criteria requires both backends running simultaneously — which strategy achieves that without a frontend code change during migration?
- **AI infrastructure timing**: Chain adapter, file marker parser, and context block loader have no Phase 1 consumer. Port them now as internal dead code, or defer to Phase 2 kickoff where they're first wired up? (Direct tension with builder principle: "no infrastructure before first user.")
- **Walker naming**: Brain dump calls it "Walker.js" in *What's Missing* and "Walker.py" in *Explicitly out of scope*. Is this a spec-doc port of an existing component or a new one — and who owns it?

## Dependencies & Sequencing

- API contract (routes, payloads, response shapes) must be locked before Flask implementation — discovered mismatches late break the zero-frontend-changes constraint
- Existing `projects/` file structure must be verified against what Flask will write before CRUD is built — if layouts diverge, migration is required
- CRUD module and chain module port can run in parallel — no Phase 1 dependency between them
- Port decision (Q1 above) must be resolved before Flask is stood up locally

## Explicitly Out of Scope

- **Chain adapter, file marker parser, context block loader** — no Phase 1 consumer; defer to Phase 2 kickoff. Re-scope when the first AI endpoint is defined.
- **Mock provider and Claude SDK provider** — same; no Phase 1 test needs them. The CRUD test suite runs without the AI chain.
- **Walker (JS or Python)** — no Phase 1 consumer named in the brain dump; defer to Phase 2 with scan endpoint.
- **Bubls-specific test fixtures** (photoshoot, tracking, waitlist, auth) — strip on copy, do not port; they test behaviour that was explicitly cut.
- **Any retry/backoff or circuit-breaker patterns** in the chain adapter — defer until Phase 2 defines failure modes for real AI calls.