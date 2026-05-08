# 🔍 Specview Phase 4 — Quality & Reliability — Analysis

## The Problem
Phases 1–3 left dead routes in `openapi.yaml` (and corresponding generated TS clients), no timeouts on skill calls, no TTL on polling job state, zero tests on the chain adapter / data / actions / Angular layers, and no written product contract. The system "works" by manual browser testing only. Phase 4 deletes the dead code, hardens the skill boundary, and writes the contract + tests that prove behavior — no new features.

## Hard Constraints
- No new AI capabilities, no new routes, no UI redesign, no infrastructure changes, no streaming work.
- `openapi.yaml` is the source of truth — Angular client is regenerated from it, not hand-edited.
- Coverage is a CI artifact, **not** a fail-fast gate (ELA lesson — hard thresholds get gamed).
- E2E uses real Angular + Flask servers; `[data-test]` is the only selector contract; page objects own selectors; scenarios seed via API.
- Session-scoped server fixture for E2E. `tmp_path` is the conftest default.
- Mock factories per service (one file per service, typed Jasmine spy).
- Module-level dict + threading.Lock for job state stays — no Redis, no queue.

## Open Questions
- **Skill runner test strategy** — `CHAIN_PROVIDER=mock` end-to-end, fixture-based skill outputs, or both layers? Shapes whether the chain adapter test is a unit or an integration.
- **Timeout model** — single 120s ceiling on every action, or per-skill `skill.json` field (e.g. brainstorm 60s, expand 15s)? Affects `actions.py` shape and skill manifest schema.
- **E2E target** — Angular dev server (fast, less prod-like) vs docker-compose (slow, prod-like). Lesson points to docker; Phase 4 needs to pick one.
- **`product-behavior.md` source** — hand-maintained doc vs auto-generated from Gherkin. Auto-gen requires tests-as-specs discipline upfront.
- **Job TTL value** — how long does an epic-guide job entry live after `done: True`? 5 min? 1 hour? Until process restart?
- **Frontend polling max retries** — count-based, time-based, or both? What does the UI show on exhaustion?

## Dependencies & Sequencing
- Dead-route cleanup (openapi.yaml → regen client → delete unused TS) blocks contract integration tests — the parametrized matrix iterates over registered routes, so the route list must be truthful first.
- Timeout + structured error envelope on `actions.py` blocks the contract matrix's error-shape assertions.
- `product-behavior.md` blocks the Gherkin features — the five feature files encode the five flows defined there.
- Mock factory files block meaningful Angular component specs.
- Session-scoped server fixture blocks E2E feature authoring.
- Skill integration test (load each SKILL.md, validate `skill.json`) blocks any test that depends on `run_skill()`.

## Explicitly Out of Scope
- New AI capabilities or new routes — re-scope only if a behavior in `product-behavior.md` cannot be expressed against existing routes.
- Streaming improvements — Phase 5.
- Hard coverage thresholds / fail-fast gates — re-scope only if a regression slips past the artifact-only model.
- Replacing the in-process job dict with Redis/queue — re-scope only if multi-worker deploy is on the table.
- Frontend redesign or new components — re-scope only if a `[data-test]` hook is genuinely unreachable in current markup.
- Auto-generating `product-behavior.md` from Gherkin in Phase 4 — defer unless the manual doc drifts within the phase.