# exec-guide Execution Report — specview-phase4

**Date:** 2026-05-08  
**Guide:** `data/projects/specview-phase4-1778223249/implementation-guide.md`  
**Commit:** `273da51` — "Phase 4: dead-route cleanup, skill hardening, tests, E2E scaffold"

---

## Tasks Run

| # | Task | Status | Agent Used |
|---|------|--------|------------|
| 1 | Dead-Route Cleanup & Client Regeneration | ✅ complete | general-purpose (spec-backend context) |
| 2 | Skill-Boundary Hardening | ✅ complete | general-purpose (spec-backend + spec-frontend context) |
| 3 | Product-Behavior Contract Document | ✅ complete | general-purpose (chain-developer context) |
| 4 | Backend Test Pyramid (Unit + Contract Matrix) | ✅ complete | general-purpose (spec-backend context) |
| 5 | Frontend Specs + Mock Factories + E2E | ✅ complete | general-purpose (spec-frontend + chain-developer context) |

---

## Skills Invoked

| Skill | When |
|-------|------|
| `/exec-guide specview-phase4-1778223249` | Orchestrated all 5 tasks |
| `/dev-test modules/ai` | After Task 4 — confirmed 766 passing |
| `/dev-review` | Post-implementation review (ran as part of close-out) |
| `/spec-pipeline` | Pre-session — generated analysis/epic/architecture/timeline |

---

## Agent Usage Detail

### Intended Routing (per exec-guide table)

| Task | Touches | Intended Agent |
|------|---------|----------------|
| Task 1 | `openapi.yaml`, `web-ng/src/app/api/`, `angular.json` | `spec-frontend` + `spec-backend` |
| Task 2 | `actions.py`, `job_store.py`, `app.component.ts`, `app.component.html` | `spec-backend` + `spec-frontend` |
| Task 3 | `product-behavior.md`, `CLAUDE.md` (doc only) | `chain-developer` |
| Task 4 | `api/modules/ai/routes/tests/`, `api/tests/integration/`, `api/modules/ai/tests/` | `spec-backend` |
| Task 5 | `web-ng/src/app/services/*.mock.ts`, `app.component.spec.ts`, `e2e/` | `spec-frontend` + `chain-developer` |

### What Was Actually Used

Plugin agents (`chain-developer`, `spec-backend`, `spec-frontend`) exist only as Claude Code CLI session agents (`.claude/agents/*.md`) — they load their reference files when invoked via `/agent-name` in an interactive session, but they **cannot be passed as `subagent_type`** to the Agent tool. The Agent tool only accepts built-in types: `general-purpose`, `Explore`, `Plan`, `claude-code-guide`.

All five tasks were executed using `general-purpose` subagents with the specialist context injected directly into the prompt — including the relevant reference files, conventions, and verification steps from the agent `.md` definitions.

**Context injected per task:**
- Tasks 1, 2, 4: `plugin/references/flask-conventions.md` + `plugin/references/testing-conventions.md` content embedded
- Task 2, 5: `plugin/references/angular-conventions.md` content embedded  
- Task 3: `product-behavior.md` design, CLAUDE.md format
- Task 5: Angular mock factory pattern + pytest-bdd E2E conventions

---

## Files Changed

### Task 1 — Dead-Route Cleanup
- `api/openapi.yaml` — removed 4 dead paths, 9 orphaned schemas
- `web-ng/src/app/api/` — regenerated; deleted `fn/ai/generate-text.ts`, `fn/ai/review-documents.ts`, `fn/operations/lint-braindump.ts`, `fn/operations/rewrite-text.ts`, and 9 model files

### Task 2 — Skill-Boundary Hardening
- `api/modules/ai/routes/actions.py` — added `_run_with_timeout()`, 120s ceiling, output-shape guard, structured error envelope
- `api/modules/ai/job_store.py` — added `JOB_TTL_SECONDS = 3600`, TTL eviction in `get_job()`
- `web-ng/src/app/app.component.ts` — added `pollingError` signal, `POLL_MAX_RETRIES = 30`, `stopPolling()`, counter logic
- `web-ng/src/app/app.component.html` — added 7 `[data-test]` selectors, polling error UI block

### Task 3 — Product-Behavior Contract
- `product-behavior.md` — 5 core flows: Brainstorm (sync), Brainstorm→Pipeline (async), Epic-Guide (async), Billing Gate (429), Pro Check
- `CLAUDE.md` — added reference to `product-behavior.md`

### Task 4 — Backend Test Pyramid
- `api/modules/ai/routes/tests/test_actions.py` — added `TestActionTimeout`, `TestActionMalformedOutput`
- `api/modules/ai/tests/test_job_store.py` — added `TestJobTTL` (3 tests)
- `api/modules/ai/routes/tests/test_skill_integration.py` — new; 44 parametrized skill-registry tests
- `api/tests/integration/test_contract_matrix.py` — new; CORS, error-envelope, OpenAPI path consistency

### Task 5 — Frontend + E2E
- `web-ng/src/app/services/ai.service.mock.ts` — `createAiServiceMock()` with 8 Jasmine spies
- `web-ng/src/app/services/projects.service.mock.ts` — `createProjectsServiceMock()` with 9 Jasmine spies
- `web-ng/src/app/app.component.spec.ts` — added polling lifecycle describe block (4 fakeAsync tests)
- `e2e/conftest.py` — session-scoped Flask (port 5001, `CHAIN_PROVIDER=mock`) + Angular (port 4201) fixtures
- `e2e/features/brainstorm.feature` — Flow 1 Gherkin
- `e2e/features/bootstrap-pipeline.feature` — Flow 2 Gherkin
- `e2e/features/epic-guide.feature` — Flow 3 Gherkin
- `e2e/features/billing-gate.feature` — Flow 4 Gherkin
- `e2e/features/pro-check.feature` — Flow 5 Gherkin

---

## Test Results

| Suite | Before | After |
|-------|--------|-------|
| Backend (pytest) | 701 | **766** |
| Frontend (Karma) | not verified this session | — |
| E2E (pytest-bdd) | 0 | scaffold only (step defs pending) |

---

## Known Gaps

- `e2e/steps/` — step definition files not written; Gherkin features exist but aren't runnable yet
- `[data-test="billing-gate-message"]` — not added; no billing gate UI element exists in the template
- CI coverage artifact (`pytest --cov` in CI yaml) — not confirmed as implemented

---

## Success Criteria Status

| Criterion | Status |
|-----------|--------|
| `openapi.yaml` declares only live routes | ✅ |
| Angular client has zero orphaned generated files | ✅ |
| Every action call enforces 120s ceiling | ✅ |
| Malformed skill output returns `{"error": ...}` not traceback | ✅ |
| Job TTL defined and evicted in `get_job()` | ✅ |
| `runtime/chain/` and `actions.py` routes have unit tests | ✅ |
| Parametrized contract matrix (CORS, error envelope, OpenAPI) | ✅ |
| Skill-integration test validates each `SKILL.md` + `skill.json` | ✅ |
| `ai.service.mock.ts` and `projects.service.mock.ts` exist | ✅ |
| `ProjectEditorComponent` polling lifecycle has meaningful specs | ✅ |
| `product-behavior.md` exists, defines all 5 flows | ✅ |
| Five Gherkin feature files exist | ✅ (step defs pending) |
| Coverage report publishable (no hard threshold) | ⚠️ CI yaml not confirmed |
| Backend test count above 701 baseline | ✅ (766) |
