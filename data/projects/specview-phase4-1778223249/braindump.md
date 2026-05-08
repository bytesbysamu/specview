# Specview Phase 4 — Quality & Reliability

## What this is

Phases 1–3 built the thin API architecture: Python does file I/O and routing, skills own all AI logic, Angular uses a generated HTTP client, and the test suite passes clean at 701 tests. The foundation is solid.

Phase 4 is about making the product genuinely reliable and explicitly correct. Not new features — confidence. We need to be able to change any part of this system and know immediately whether something broke. We need to know that the product behaves the way we think it does, and we need the codebase to be clean enough that a new developer (or a future me) can understand it without archaeology.

This is a housekeeping + hardening phase. No new AI capabilities. No new user-visible features. Just: kill dead code, define the product contract, write the tests that prove the contract is met.

## The four problems

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

701 tests pass. But the coverage map has white space:

**Uncovered backend modules:**
- `api/modules/runtime/chain/` — zero tests. The adapter boundary is the most critical code in the system (every AI call goes through it) and it has no test coverage.
- `api/modules/data/` — no tests for the file loading utilities the bootstrap chain depends on.
- `api/modules/ai/routes/actions.py` — the 8 new action routes added in Phase 3 have no dedicated tests. They're covered implicitly by manual testing only.
- Skill layer integration — no test exercises the full path from HTTP request → `run_skill()` → SKILL.md execution. The skill runner is tested as a black box.

**Uncovered frontend:**
- `web-ng/src/app/` has exactly one spec file: `app.component.spec.ts`, which tests that the app title is "specview". That's it. Every service, every component, every signal — untested.
- The polling logic in `ProjectEditorComponent` (epic guide status polling with `setInterval`) is a known source of bugs. No test catches a missing `clearInterval`.
- `ai.service.ts` — the facade that bridges the generated HTTP client — has no tests. Its error handling path (what happens when the API returns 500) is untested.

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

None of this is written down. It lives in the code and in someone's head. Phase 4 should produce a `product-behavior.md` that defines each of these flows explicitly, and the test suite should prove the contract is met.

## What we're not doing

- No new AI capabilities
- No new routes
- No frontend design changes
- No infrastructure changes
- No streaming improvements (Phase 5 territory)

## The outcome

After Phase 4:
- `openapi.yaml` matches `flask routes` exactly. No dead routes, no generated dead files.
- Every HTTP request to `actions.py` has a timeout ceiling of 120s. Malformed skill output returns a 500 with a structured error, not a Python traceback.
- Epic guide polling has max retries (frontend) and job TTL (backend). The infinite poll loop is impossible.
- `runtime/chain/`, `data/`, and `ai/routes/actions.py` have unit test coverage.
- Angular services and the polling component have meaningful spec coverage — not just "it compiles."
- A `product-behavior.md` document exists and is referenced from CLAUDE.md.
- The skill integration test runs in CI: load each SKILL.md, validate `skill.json`, confirm the skill runner can instantiate the skill without an AI call.

The product doesn't change. The confidence does.

## Open questions

How do we test the skill runner without making a real Claude call? Mock provider? Fixture output? The right answer shapes the integration test design.

What is the right timeout per action? Brainstorm might need 60s, expand probably needs 15s. Is a single ceiling OK or do we need per-skill configuration in `skill.json`?

Frontend testing: do we write Jasmine specs for every component, or is a subset of critical paths enough? The polling component and the billing gate are non-negotiable. Everything else is a judgment call.

Should `product-behavior.md` be a living document maintained manually, or should it be auto-generated from the test descriptions? The latter is more sustainable but requires the tests to be written as specifications, not just assertions.
