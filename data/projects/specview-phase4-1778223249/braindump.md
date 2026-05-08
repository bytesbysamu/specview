# Specview Phase 4 — Quality & Reliability

## What this is

Phases 1–3 built the thin API architecture: Python does file I/O and routing, skills own all AI logic, Angular uses a generated HTTP client, and the test suite passes clean at 701 tests. The foundation is solid.

Phase 4 is about making the product genuinely reliable and explicitly correct. Not new features — confidence. We need to be able to change any part of this system and know immediately whether something broke. We need to know that the product behaves the way we think it does, and we need the codebase to be clean enough that a new developer (or a future me) can understand it without archaeology.

This is a housekeeping + hardening phase. No new AI capabilities. No new user-visible features. Just: kill dead code, define the product contract, write the tests that prove the contract is met.

## The five problems

### 1. Dead code is lying to us

The openapi.yaml still declares routes that were deleted in Phase 3. The Angular API client was regenerated from it — so there are generated TypeScript service files that call endpoints that don't exist. The frontend imports those services even though nothing uses them. We're living with a fake API contract.

Concrete dead routes in openapi.yaml (from Phase 3 deletion):
- `POST /api/ai/text/rewrite` — gone
- `POST /api/ai/text/generate` — gone
- `POST /api/ai/text/lint-braindump` — gone
- `POST /api/ai/text/review` — gone

Generated TypeScript files that correspond to deleted routes exist in `web-ng/src/app/api/`. Dead imports, dead services, zero usage. They confuse the reader and inflate the bundle.

The fix is simple: update openapi.yaml to reflect only what the Flask routes actually serve, regenerate the Angular client, and verify nothing breaks. The openapi.yaml becomes the source of truth again.

### 2. The skill layer has reliability gaps

The generic action route at `api/modules/ai/routes/actions.py` calls `run_skill()` and returns the result. What happens when the Claude CLI takes 90 seconds? No timeout is set. The gunicorn worker blocks forever until the 900-second server timeout. One stuck request ties up a thread.

What happens when a skill returns valid JSON but without the expected `text` key? A `KeyError` propagates to a 500 with no useful message. The caller gets "Internal server error" — no hint of what failed or why.

The epic guide polling has a hidden infinite loop risk. The job status dict is module-level. If the epic guide job crashes without writing `done: True`, the frontend polls forever. There is no max-retries on the backend side, no TTL on job state, and the frontend polling only stops when `done` is true.

These aren't hypothetical. The brainstorm 500 we just fixed was exactly this pattern — a skill returning an unexpected shape, Python crashing, frontend showing "Could not reach AI."

### 3. Test coverage has large blind spots

701 tests pass. But the coverage map has white space.

**The test pyramid is incomplete.** Based on prior lessons building this exact stack, the failure modes that actually hit production are integration-level failures, not unit-level failures: a silent template fallback on AI error, a cross-test module leak in full-suite ordering, a route that exists in the code but not in CORS configuration. Unit tests cannot catch these. A three-layer pyramid is required: unit → contract integration → E2E.

**Uncovered backend modules:**
- `api/modules/runtime/chain/` — zero tests. The adapter boundary is the most critical code in the system (every AI call goes through it) and it has no test coverage. The `CHAIN_PROVIDER=mock` path is never exercised; neither is the CLI provider path end-to-end.
- `api/modules/data/` — no tests for the file loading utilities the bootstrap chain depends on.
- `api/modules/ai/routes/actions.py` — the 8 new action routes added in Phase 3 have no dedicated tests. They're covered implicitly by manual testing only.
- Skill layer integration — no test exercises the full path from HTTP request → `run_skill()` → SKILL.md execution. The skill runner is tested as a black box.

**Missing contract integration tests:**
The existing test suite bypasses WSGI serialisation via Flask's test client and runs entirely against `CHAIN_PROVIDER=mock`. This means: CORS headers are never verified, error envelope shape (`{"error": "..."}`) is never checked across all routes systematically, OpenAPI response schemas are never validated against actual route output, and the `CHAIN_PROVIDER=cli` path has zero test coverage. Any of these could be broken silently. A parametrized contract matrix — one test class per concern, all registered routes as the parametrize input — would catch every new route that violates the envelope or CORS policy automatically.

**Uncovered frontend:**
- `web-ng/src/app/` has exactly one spec file: `app.component.spec.ts`, which tests that the app title is "specview". That's it. Every service, every component, every signal — untested.
- The polling logic in `ProjectEditorComponent` (epic guide status polling with `setInterval`) is a known source of bugs. No test catches a missing `clearInterval`.
- `ai.service.ts` — the facade that bridges the generated HTTP client — has no tests. Its error handling path (what happens when the API returns 500) is untested.
- No per-service mock factory files exist. Without mock factories, writing component tests requires duplicating spy setup inline — every component test reinvents the same stubs independently and they drift apart.

**Missing integration tests:**
- No test verifies that the skills in `plugin/skills/` are syntactically valid and can be loaded by the skill runner.
- No test exercises the brainstorm → spec-pipeline handoff. A user accepts the brainstorm output and starts the pipeline — that flow is unverified end-to-end.

### 4. Product behavior is not explicitly defined

We built a product. But "the product works" is based on manual browser testing, not a written contract. When we change something, we have no way to know whether the behavior changed intentionally or accidentally.

What are the actual product behaviors we care about?

- A user pastes a braindump and clicks Brainstorm. What happens? How long does it take? What does failure look like?
- A user accepts the brainstorm and starts the spec pipeline. What steps run? What order? What does partial completion look like?
- A user generates an epic guide. What triggers it? Can they generate it twice? What happens if they navigate away mid-generation?
- The billing gate: free users hit a usage limit. Which actions are limited? Which are not? What does the limit error look like in the UI?
- Pro users get unlimited usage. What defines "Pro"? Is the check synchronous or cached?

None of this is written down. It lives in the code and in someone's head. Phase 4 should produce a `product-behavior.md` that defines each of these flows explicitly. The E2E test suite should then prove the contract is met — five Gherkin feature files covering the five core workflows, each seeded via API before the browser step begins.

### 5. No E2E layer — the highest-risk surface is unprotected

The bootstrap workflow (braindump → spec pipeline) is the core value loop of the product. It is also the most complex path: it involves the Angular UI, the HTTP layer, background jobs, polling, and file writes. It has never been exercised by an automated test. Manual smoke testing is the current safety net.

Prior experience building this stack produced specific lessons about E2E:
- Assertions written without a live runner are claims, not measurements.
- Route renames, template changes, and broken API contracts are integration failures — they do not appear under filesystem interaction or a mocked layer.
- Browser tests must use real servers (Angular dev + Flask). A stub that bypasses HTTP is testing the step definitions, not the product.
- `[data-test]` attributes are the only selector contract. Class names, element IDs, and tag structures change when the product is redesigned; they are visual implementation details, not behavioral contracts.
- Page objects are the single place where selectors live. Step definitions call methods, not selectors.
- E2E scenarios seed state via API before the browser step begins — UI tests start at the assertion-relevant moment, not the beginning of the flow.

## What we're not doing

- No new AI capabilities
- No new routes
- No frontend design changes
- No infrastructure changes
- No streaming improvements (Phase 5 territory)

## Lessons from prior work on this stack

**ELA's documented lesson on coverage thresholds:** Hard local thresholds produce gamed line coverage — empty branches and trivial assertions added to hit numbers, not meaningful behavioral coverage. Coverage is surfaced as CI artifacts, not enforced as fail-fast gates.

**Factory fixtures over inline data:** Named factory functions that return fully-formed request dicts replace repeated inline JSON strings. When a route's required field names change, one factory function update propagates to every test. Without factories, a field rename requires a search-and-replace across all test files.

**Parametrize over duplicate:** One test class covers all eight action routes for missing-field and malformed-output cases — per-route duplication is replaced by a single parametrized matrix. Adding a new route means adding one entry to the parametrize list.

**Default isolation, not opt-in:** `tmp_path` is the conftest default for all filesystem-touching tests. Isolation is automatic, not a per-test opt-in that individual tests can forget.

**pytest classes for organization:** `pytest tests/test_project.py::GetProject -v` runs a focused slice. Grouping by HTTP verb and scenario makes the test's concern legible at a glance.

**Syrupy for prompt snapshots:** Any change to a prompt function or system message produces a visible diff in the PR, not a silently passing test. `--snapshot-update` regenerates all goldens in one command.

**Session-scoped server fixture for E2E:** Function-scoped setup makes a 5-feature suite 5× slower for no isolation benefit, since state is reset by API calls inside the tests, not by server restarts.

**Mock factories for frontend services:** Per-service mock factory files (`ai.service.mock.ts`) export a `createMockAiService()` function returning a typed Jasmine spy. Component tests import the factory and receive a consistent mock without duplicating setup. Without factories, component tests reinvent the same stubs and drift.

## The outcome

After Phase 4:
- `openapi.yaml` matches Flask routes exactly. No dead routes, no generated dead files.
- Every HTTP request to `actions.py` has a timeout ceiling of 120s. Malformed skill output returns a 500 with a structured error, not a Python traceback.
- Epic guide polling has max retries (frontend) and job TTL (backend). The infinite poll loop is impossible.
- `runtime/chain/`, `data/`, and `ai/routes/actions.py` have unit test coverage.
- A parametrized contract integration test matrix covers CORS, error envelope, and OpenAPI response shape across all registered routes.
- Angular services and the polling component have meaningful spec coverage — not just "it compiles."
- Per-service mock factory files exist for `ai.service.ts` and `projects.service.ts`.
- Five Gherkin feature files cover the five core workflows end-to-end.
- A `product-behavior.md` document exists and is referenced from CLAUDE.md.
- The skill integration test runs in CI: load each SKILL.md, validate `skill.json`, confirm the skill runner can instantiate the skill without an AI call.
- Coverage is surfaced as a CI artifact — not a build gate.

The product doesn't change. The confidence does.

## Open questions

How do we test the skill runner without making a real Claude call? Mock provider? Fixture output? The right answer shapes the integration test design.

What is the right timeout per action? Brainstorm might need 60s, expand probably needs 15s. Is a single ceiling OK or do we need per-skill configuration in `skill.json`?

Should the E2E suite run against the Angular dev server on localhost, or against the Docker-compose stack? Dev server is faster; Docker is closer to production. The prior lesson: real servers, not mocks — Docker is the safer default.

Should `product-behavior.md` be a living document maintained manually, or should it be auto-generated from Gherkin feature files? The latter is more sustainable but requires the tests to be written as specifications, not just assertions.
