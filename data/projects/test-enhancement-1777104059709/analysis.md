# 🔍 Test Enhancement — Analysis

## The Problem
spec-doc-api has 250 backend tests proving endpoints work in isolation but zero real-HTTP integration tests and zero E2E coverage. Two production bugs — silent template fallback on AI failure and a cross-test module leak — surfaced via manual smoke because the layer that would have caught them doesn't exist. This epic closes that gap by applying the ELA test pyramid to the current Python/Angular stack.

## Hard Constraints
- **Karma + Jasmine is the Angular test runner, not Jest.** `syrupy` is Python-only — `generateSpecIndex()` and `generateTimeline()` are TypeScript and cannot be snapshot-tested with it. A frontend snapshot mechanism is undecided.
- **Express is retired.** pytest is the sole backend runner. No Node-side backend tests.
- **SDK over subprocess.** `pytest-httpserver` Claude stubs must return realistic Anthropic SDK response shapes, not raw text, or the real provider path remains untested.

## Open Questions
- **Angular component test strategy** — brain dump dismisses TestBed vs shallow-render but doesn't decide. Full TestBed or a render wrapper? Determines how all 15 component specs are structured.
- **Frontend snapshot mechanism** — `generateSpecIndex()` / `generateTimeline()` are TypeScript. Options: Karma `toEqual` against a committed golden object, inline `toMatchSnapshot` if Jasmine 4+ supports it, or skip snapshots for TS generators entirely. Needs a decision before Task 3.
- **E2E runner** — brain dump proposes `pytest-playwright` (Python) *and* lists `@playwright/test` in package.json. One runner or two? Python-only is simpler; TS runner shares fixture style with Angular specs.
- **CI job mapping** — which markers run on push vs PR vs manual? Dorny path-change detection needs explicit job assignments for the five new markers.

## Dependencies & Sequencing
- Task 1 (reorganization + conftest fixtures) blocks Tasks 4, 5, 6 — contradicts the brain dump's "Tasks 1–3 can parallelize" claim; correct before writing the epic.
- Frontend service specs (Task 2) block component tests — mock factory pattern is established here.
- `[data-test]` retrofit (Task 5) blocks all E2E feature files (Task 6).
- Tasks 2 and 3 can parallel each other; Task 4 can parallel both.

## Explicitly Out of Scope
- **`@playwright/test` in package.json** — one language, one E2E runner. Remove from the epic. Re-scope if an Angular-native need emerges pytest-playwright can't serve.
- **`real_claude` test authoring** — the marker system is in scope; writing the actual Claude API stubs is not. No named consumer until Task 4's httpserver tests prove the provider path works. Re-scope after Task 4 stabilises.
- **ELA→Python translation table + inline code blocks** (Makefile targets, pyproject.toml markers, requirements-dev.txt) — implementation guide content only; strip before the epic is written.
- **"Coverage targets per epic" tracking table** — status tracking belongs in timeline.md, not the epic.