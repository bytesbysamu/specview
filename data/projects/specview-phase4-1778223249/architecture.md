# 🏗️ Solution Architecture: Specview Phase 4 — Quality & Reliability

## Architecture Overview

Phase 4 is not new construction — it is structural reinforcement on a working building. The mental model is a **trust pyramid**: at the base sits the OpenAPI contract (must match reality), above it the skill boundary (must fail predictably), then the test pyramid (must catch what manual testing misses), and at the apex the product-behavior contract (must be explicit, not folkloric). Each layer reinforces the one above it. Removing dead routes makes the contract truthful; hardening the skill boundary makes failures structured; the test pyramid proves the contract holds; the behavior document tells the pyramid what "holds" means.

The key insight is that **integration failures, not unit failures, dominate production incidents on this stack** — silent template fallbacks, broken CORS configs, route renames, polling loops without `clearInterval`. Unit tests cannot catch any of these. The architecture therefore invests deliberately in a **parametrized contract matrix** at the integration tier and a **real-server Gherkin layer** at the E2E tier, while keeping unit tests narrowly focused on adapter logic and service code where they have leverage. This is a pyramid weighted by where bugs actually live, not by what is fastest to write.

The components fit the existing thin-API shape with no new boundaries: the chain adapter remains the only AI seam, the in-process job dict remains the only state, and the skill runner remains the only path from HTTP to AI. Phase 4 adds reliability rails (timeout, error envelope, TTL, max-retries) on the existing seams and adds testing infrastructure (mock factories, page objects, contract matrix) that observes those seams. Nothing new is invented; existing contracts become enforceable.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P1 — Adapter Boundary** | The chain adapter is the only point where AI provider behavior is mocked; all unit tests for `ai/routes/` flip `CHAIN_PROVIDER=mock` rather than monkey-patching individual call sites. The adapter itself gets dedicated unit tests so the boundary is verified, not assumed. |
| **P2 — Thin HTTP Layer** | Skill-boundary hardening (timeout, error envelope) lives in the skill runner / `actions.py` adapter — not duplicated across route handlers. Routes remain validate → call → return. |
| **P3 — Async 202 + Polling** | The job-state TTL and frontend max-retries rails extend the existing pattern; they do not replace it. Module-level dict + `threading.Lock` is preserved — Phase 4 adds expiry and bounded polling around it, not Redis. |
| **P4 — No Speculative Abstractions** | The contract matrix is parametrized over registered routes (one concrete iteration per route that exists today), not designed as a generic test framework. The skill integration test loads real `SKILL.md` files, not a hypothetical skill loader API. |
| **P5 — OpenAPI-First** | Dead-route cleanup re-establishes `openapi.yaml` as the contract; the contract matrix then validates each route against the schema it declares. The OpenAPI document is restored to authoritative status. |
| **P6 — OpenClaw Plugin Principles** | Skill integration test validates `SKILL.md` + `skill.json` shape — the references-as-source-of-truth rule is enforced by automation, not convention. |
| **P7 — File Size & Structure** | Per-service mock factory files (`*.service.mock.ts`) are tiny named-export modules — one factory per service, kept under the 200-line ceiling and reused across every consuming spec. |

## Component Design

### Dead-Route Cleanup Layer

**Purpose**: Restore `openapi.yaml` as the truthful contract by removing four deleted routes (`text/rewrite`, `text/generate`, `text/lint-braindump`, `text/review`) and the generated TypeScript artefacts that mirror them.

**Mental model**: This is not a code change — it is a **lie correction**. The OpenAPI document currently declares routes that do not exist. Every downstream consumer (the Angular generator, future contract tests, future readers) inherits that lie. Phase 4 cannot run a contract matrix against `openapi.yaml` until the document is true. Cleanup is therefore a **prerequisite**, not a parallel task — it is what makes every other test in the phase meaningful.

**Boundary discipline**: The Angular `api/` directory is generated, not hand-edited. Cleanup operates on `openapi.yaml` and re-runs the generator; orphaned files are deleted because they are no longer produced, not because they are individually pruned. This preserves the rule that generated code is never hand-edited.

### Skill-Boundary Hardening Layer

**Purpose**: Make every failure mode at the skill seam **structured, bounded, and observable** — no infinite waits, no Python tracebacks reaching the client, no orphaned job state.

**Four rails**, each addressing a documented failure mode:

1. **120s timeout ceiling on `actions.py`** — A single per-action timeout (not per-skill configuration) because the only skill that benefits from custom timeouts is brainstorm, and the cost of a `skill.json` schema extension exceeds the cost of one ceiling that fits all current skills. If a future skill needs more, it gets a per-skill override then — not now (P4).
2. **Structured error envelope** — Malformed skill output (missing `text` key, invalid JSON, runtime exception inside the skill) is caught at the runner boundary and converted to `{"error": "..."}` with a 500 status. The envelope shape becomes a contract the matrix tests enforce.
3. **Job-state TTL on the backend** — Module-level job dict entries expire after a defined window. A crashed job that never wrote `done: True` no longer occupies memory or confuses polling clients indefinitely.
4. **Max-retries on the frontend** — Polling stops after a bounded count with a user-visible error state. The infinite-poll loop becomes structurally impossible — not just unlikely.

**Why all four**: Each rail closes a distinct failure path. Timeout closes "Claude hangs," envelope closes "skill returns garbage," TTL closes "job thread crashes silently," max-retries closes "frontend never gives up." Removing any one leaves a path open. The rails are cheap individually and only meaningful together.

### Test Pyramid

**Purpose**: Convert "the product works" from manual claim to repeatable measurement, weighted toward the failure modes that actually occur.

**Three tiers, each with a specific job:**

- **Unit tier** — `runtime/chain/`, `data/`, and the eight `actions.py` routes. Catches logic errors at the adapter boundary and in pure-Python services. Fast, deterministic, runs constantly.
- **Contract integration tier** — One parametrized class per concern (CORS, error envelope, OpenAPI response shape), iterating over every registered route. Catches the integration failures that dominate production: a route added without CORS, an envelope missing on error, a response that drifts from the schema. **The matrix structure is the architecture choice** — adding a new route means adding one parametrize entry, not writing a new test file.
- **E2E tier** — Five Gherkin feature files mapping 1:1 to the five flows in `product-behavior.md`. Real Angular dev server, real Flask. Catches the cross-layer failures (route rename, broken polling, CORS misconfig) that no lower tier can see.

**Skill integration test** sits between unit and contract tiers: it loads each `plugin/skills/*/SKILL.md`, validates the corresponding `skill.json` schema, and confirms the skill runner can instantiate without making an AI call. This catches the "we renamed a skill and forgot to update the loader" class of bug — a Phase 3 risk that is currently unprotected.

### Product-Behavior Contract

**Purpose**: Define what the product **does** in writing, so Phase 4 tests have an explicit target and Phase 5+ has an explicit baseline to change against.

The document defines five flows: braindump→brainstorm, brainstorm→pipeline, epic-guide generation, billing gate, Pro check. Each flow has trigger, expected steps, expected duration class, and expected failure shape. The Gherkin feature files mirror these one-to-one; the document is the spec, the features are the proof.

**Why manual now, not auto-generated**: Auto-generation from Gherkin requires the features to be written as specifications first — a chicken-and-egg problem. Phase 4 writes both deliberately and accepts the duplication risk. If the document drifts within Phase 4, that is a signal to revisit; otherwise the cost of a generation pipeline exceeds its current value (P4).

### Frontend Test Infrastructure

**Purpose**: Make Angular component testing cheap enough that it actually happens, without the per-test stub duplication that causes drift.

**Per-service mock factory files** (`ai.service.mock.ts`, `projects.service.mock.ts`) export a single named factory function returning a typed Jasmine spy. Every consuming spec imports the factory rather than rebuilding spies inline. This is the architectural choice — without factories, component tests reinvent stubs and they diverge silently. With factories, a service signature change updates one file and propagates.

**Polling-lifecycle spec for `ProjectEditorComponent`** specifically targets the `setInterval`/`clearInterval` contract — the exact bug class flagged in the analysis as a known source of incidents. The spec is not "it compiles"; it is "polling stops on success, stops on max-retries, stops on component destroy."

### CI Coverage Artifact

**Purpose**: Surface coverage data without enforcing it as a gate.

**Why no threshold**: Documented prior lesson — hard thresholds get gamed via empty branches and trivial assertions. Coverage as artifact lets a human read the trend over time and notice meaningful regressions; coverage as gate just teaches the test suite to lie. The architecture choice is **observability over enforcement**.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend tests | pytest with classes + parametrize | Already in use; classes group by HTTP verb/scenario for legibility; parametrize is the mechanism for the contract matrix |
| Test isolation | `tmp_path` as conftest default | Default-on isolation; per-test opt-in is forgettable, opt-out is deliberate |
| Prompt regression | Syrupy snapshots | Prompt drift becomes a visible PR diff, not a silent pass; one-command regeneration |
| AI mocking | `CHAIN_PROVIDER=mock` end-to-end | Existing infrastructure, exercises the real adapter path rather than monkey-patching call sites (P1) |
| Frontend tests | Karma + Jasmine (existing) | Already wired in `web-ng/`; no new framework introduced; per-service mock factories address the real gap |
| E2E framework | `pytest-playwright + pytest-bdd` + real Flask + real Angular dev server | Single test runner across unit, integration, and E2E; pytest fixtures and parametrize available in step definitions; no second JS runtime |
| E2E selectors | `[data-test]` attributes only | Class names and tag structures are visual implementation details that change with redesigns; data-test is the behavioral contract |
| E2E setup | Session-scoped server fixture, API-seeded state | Function-scoped restart is 5× slower for no isolation benefit; state is reset via API, not server lifecycle |
| Coverage | pytest-cov → CI artifact | Surface, don't enforce |
| Job state | Module-level dict + `threading.Lock` (existing) + TTL | Single-worker deploy makes Redis unnecessary (P3); TTL is the minimal addition that closes the leak |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Single 120s timeout in `actions.py`, not per-skill | One ceiling fits every current skill; per-skill config is a `skill.json` schema extension with no concrete consumer | A future skill needing >120s requires the schema work then; accepted because no such skill exists today (P4) |
| Parametrized contract matrix over per-route tests | Adding a route means one parametrize entry, not a new file; concerns (CORS, envelope, schema) stay in one place | Matrix failures require reading the parametrize ID to identify the failing route; outweighed by the maintenance win |
| `product-behavior.md` written manually, not generated | Auto-generation requires features-as-specs upfront; chicken-and-egg in Phase 4 | Manual document can drift from Gherkin; mitigated by 1:1 mapping rule and the small flow count (5) |
| Angular dev server for E2E, not full Docker stack | Faster feedback loop; the load-bearing decision is real servers vs mocked — both use real Flask and real Angular; Docker parity added if a gap surfaces | Slightly less production-like; acceptable because route renames and template failures are caught by real Angular + Flask regardless of orchestration |
| Mock factory file per service, not a shared mocks barrel | Per-service factories keep imports explicit and the file size principle (P7) honored | Slightly more files; outweighed by drift prevention and named-export clarity |
| Coverage as CI artifact, no fail-fast threshold | Documented ELA lesson: thresholds get gamed | No automatic merge block on coverage regression; mitigated by trend-over-time visibility |
| Skill integration test instantiates without AI call | Tests the loader/schema contract, not the AI provider; deterministic and fast | Does not catch AI-shape regressions; those are caught by mock-provider unit tests at the adapter tier |
| Job-state TTL, not migration to a queue | In-process dict + TTL closes the leak; queue introduces a new dependency for a single-worker deploy | Cross-process job sharing remains impossible; accepted because the deploy is single-worker by design (P3) |
| Frontend max-retries with user-visible error, not silent stop | Failure must be observable to the user, not a silent UI freeze | Slight UX work to design the error state; outweighed by the elimination of the infinite-poll class entirely |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking