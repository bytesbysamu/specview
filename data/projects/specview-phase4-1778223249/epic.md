# 🎯 Epic: Specview Phase 4 — Quality & Reliability

## Business Value

Phases 1–3 shipped the thin-API architecture (Python routes file I/O, skills own AI logic, Angular consumes a generated client). The product works — but "works" is currently proven by manual browser clicks, not by anything repeatable. Every change ships with the implicit hope that nothing important broke. As the surface area grows, that hope becomes the bottleneck on velocity.

Phase 4 converts that hope into evidence. Killing dead routes restores `openapi.yaml` as a truthful contract; hardening the skill boundary stops one stuck Claude call from tying up a worker; a written `product-behavior.md` plus a three-layer test pyramid (unit → contract → E2E) means we can change any part of this system and know within a CI run whether behavior held. The payoff is direct: faster iteration on Phase 5+ features, fewer production regressions, and a codebase a future-me (or a new collaborator) can read without archaeology.

The economic logic is internal — Sam pays in time. The cost of one production regression caught by a user is higher than the cost of writing the contract test that would have caught it. Phase 4 front-loads that cost so the next phase doesn't pay it.

## Scope

### What This Epic Covers

- **Dead-code cleanup** — prune deleted routes from `openapi.yaml`, regenerate the Angular client, delete orphaned TS service files
- **Skill-boundary hardening** — 120s timeout ceiling on `actions.py`, structured error envelope on malformed skill output, frontend polling max-retries, backend job-state TTL
- **Backend test coverage** — unit tests for `runtime/chain/`, `data/`, and the eight `ai/routes/actions.py` routes; skill-integration test that loads each `SKILL.md` and validates `skill.json`
- **Contract integration matrix** — one parametrized test class per concern (CORS, error envelope, OpenAPI response shape) iterating over every registered route
- **Frontend test coverage** — per-service mock factory files (`ai.service.mock.ts`, `projects.service.mock.ts`), specs for Angular services, and a polling-lifecycle spec for `ProjectEditorComponent`
- **Product-behavior contract** — `product-behavior.md` defining the five core flows (braindump→brainstorm, brainstorm→pipeline, epic-guide generation, billing gate, Pro check); CLAUDE.md updated to reference it
- **E2E layer** — five Gherkin feature files matching `product-behavior.md`, real Angular + Flask servers, session-scoped server fixture, `[data-test]` selector contract, page objects, API seeding
- **CI coverage artifact** — coverage surfaced per run, not enforced as a fail-fast gate

### What This Epic Does NOT Cover

- ❌ **New AI capabilities or routes** — Phase 4 hardens what exists; new behavior is Phase 5+
- ❌ **Streaming improvements** — explicit Phase 5 territory
- ❌ **Frontend redesign or new components** — re-scope only if a `[data-test]` hook is genuinely unreachable in current markup
- ❌ **Hard coverage thresholds / fail-fast gates** — ELA's documented lesson: thresholds get gamed
- ❌ **Replacing the in-process job dict with Redis or a queue** — single-worker deploy; module-level dict + `threading.Lock` stays
- ❌ **Auto-generating `product-behavior.md` from Gherkin** — manual doc this phase; revisit only if it drifts within Phase 4
- ❌ **Infrastructure changes** — no Docker/Coolify/nginx work

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Dead-Route Cleanup & Client Regeneration** | None | — | 0.5 days | High |
| 2 | **Skill-Boundary Hardening** | None | with #1 | 1 day | High |
| 3 | **Product-Behavior Contract Document** | None | with #1, #2 | 0.5 days | High |
| 4 | **Backend Test Pyramid (Unit + Contract Matrix)** | #1, #2 | — | 2 days | High |
| 5 | **Frontend Specs + Mock Factories + E2E Gherkin** | #1, #3, #4 | — | 2.5 days | High |

## Success Criteria

- ✅ `openapi.yaml` declares only routes that exist in Flask; `web-ng/src/app/api/` contains zero generated files for deleted routes; `npm run build` passes
- ✅ Every action call through `actions.py` enforces a 120s ceiling and returns `{"error": "..."}` (not a Python traceback) on malformed skill output
- ✅ Epic-guide job entries expire after a defined TTL; frontend polling stops on a defined max-retries with a user-visible error state
- ✅ `runtime/chain/`, `data/`, and the eight `actions.py` routes have dedicated unit tests; `CHAIN_PROVIDER=mock` is exercised end-to-end
- ✅ A parametrized contract matrix runs against every registered route covering CORS headers, error-envelope shape, and OpenAPI response schema
- ✅ A skill-integration test loads each `plugin/skills/*/SKILL.md`, validates the corresponding `skill.json`, and confirms the runner can instantiate without an AI call
- ✅ `ai.service.mock.ts` and `projects.service.mock.ts` exist; Angular services and `ProjectEditorComponent` polling lifecycle have meaningful specs (not "it compiles")
- ✅ `product-behavior.md` exists, defines all five flows, and is linked from `CLAUDE.md`
- ✅ Five Gherkin feature files run against real Angular + Flask servers using a session-scoped fixture, `[data-test]` selectors, page objects, and API seeding
- ✅ Coverage report is published as a CI artifact on every run; no hard threshold blocks merge
- ✅ Total backend test count increases meaningfully above the 701 baseline; full suite runs clean

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking