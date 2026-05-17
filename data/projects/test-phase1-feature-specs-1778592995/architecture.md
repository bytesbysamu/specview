# 🏗️ Solution Architecture: Test Phase 1: Feature Specs & Testing Architecture

## Architecture Overview

This phase produces a document, not software. The deliverable is a single markdown file containing every user-facing feature of the Specview overview page and SaaS flows, structured as testable specifications with stable numbering. Phases 2 and 3 consume this document mechanically — Gherkin scenarios derive from the spec's expected behaviors, unit tests derive from the spec's edge cases. The architecture problem is therefore one of information design: how to structure specifications so they are discoverable, unambiguous, derivable, and stable under feature evolution.

The central insight is that the draft F1–F17 inventory is incomplete by design. Ten epic branches shipped features across authentication, billing, isolation, layout, and navigation — some of which introduced entirely new components (upgrade page, usage meter, billing interceptor) while others modified existing features in ways the draft list does not capture. The architecture must separate the discovery process (Task 1) from the specification process (Tasks 2–3) and define a format that survives re-numbering without breaking downstream references.

The testing architecture map is the second structural deliverable. It defines four layers — feature specs, Gherkin scenarios, E2E tests, and unit tests — and maps every discovered feature to its current coverage state across those layers. This map turns "what should we test next?" from an exploratory question into a lookup. The map also resolves a structural tension: existing E2E tests cover backend API flows while existing unit tests cover two pure-logic services, leaving the entire frontend interaction surface unmapped.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | Specs describe features that exist in the shipped codebase today. No placeholder specs for planned features. No generic spec templates for features that might exist — every spec entry traces to a real file and a real behavior. |
| P5 — OpenAPI-First (adapted) | The feature spec document is the contract. Gherkin scenarios implement it. Unit tests implement it. When a feature changes, the spec updates first and tests follow — never the reverse. This mirrors the OpenAPI-first pattern but applied to behavioral requirements rather than HTTP endpoints. |
| P1 — Adapter Boundary (testing implication) | Every spec must be verifiable against `CHAIN_PROVIDER=mock`. Specs that describe AI-dependent behavior define the mock boundary explicitly: what the mock returns, what the feature does with that return value. No spec requires a live AI call or real Stripe session. |
| P7 — File Size & Structure | The feature spec document will exceed 200 lines by necessity — it catalogs 25+ features. The architecture accommodates this by defining a rigid per-feature structure that makes the document navigable by section heading rather than requiring sequential reading. |
| Discovery over assumption | The draft F1–F17 list is treated as a starting hypothesis, not a source of truth. Task 1 scans the actual codebase and all ten impl guides to build the verified inventory. Features found in code but missing from the draft get added. Draft entries not found in code get removed. |

## Component Design

### Component 1: Feature Discovery Engine (Task 1)

**Purpose**: Produce a complete, verified inventory of every user-facing feature by scanning source files and implementation records rather than trusting a manually curated list.

The discovery process has two inputs: the live codebase and the implementation records from all ten executed epic branches. The codebase scan covers templates, components, routes, services, interceptors, and state files in `web-ng/src/app/`. The implementation records are the `implementation-guide.md` and `exec-guide-summary.md` files from each of the ten project directories under `data/projects/`. Each input catches what the other misses — code shows what exists now, impl guides show what was intentionally shipped and may reveal behaviors not obvious from reading templates alone.

The output is a numbered feature list organized into two domains: overview page features and SaaS features. Each entry includes a short name, the primary source file, and enough description to scope the subsequent spec. Numbering uses a simple monotonic scheme with domain prefixes — `OV-` for overview page, `SA-` for SaaS and auth — to allow inserting new features without renumbering existing ones. The draft F1–F17 labels are retired; they served their purpose as a brainstorming artifact but cannot be the stable identifiers that Phases 2 and 3 need.

### Component 2: Feature Spec Format (Tasks 2–3)

**Purpose**: Define a repeatable structure for each feature specification that makes it mechanically derivable into Gherkin scenarios and unit test cases.

Each feature spec follows a fixed five-section structure. The **summary** states what the feature does in one sentence. The **inputs** section lists every signal, service call, route parameter, or user action that triggers the feature. The **expected outputs** section defines the observable result — what the user sees, what state changes, what the DOM contains — in terms that a Playwright assertion or Karma expectation can verify. The **state matrix** enumerates the meaningful combinations of inputs and their corresponding outputs, presented as a decision table rather than prose. The **edge cases** section captures at least one boundary condition per feature: what happens when the input is missing, when the service errors, when the value is at a limit.

This format is deliberately not Gherkin. Gherkin is Phase 2's concern. The spec format is more compact and allows expressing state matrices that would be verbose as Given/When/Then triplets. The Phase 2 pipeline reads the state matrix and generates one Gherkin scenario per row — the spec is the generator, not the test.

The mock contract annotation is critical. Every spec that involves an external dependency — AI chain, Stripe billing, JWT auth — includes a "Mock Boundary" note that states what `CHAIN_PROVIDER=mock` returns or what the test fixture provides. This ensures no spec author writes a requirement that can only be verified with a live service.

### Component 3: Testing Architecture Map (Task 4)

**Purpose**: Provide a single-page answer to "what is tested, what is not, and where does a new test go?" for every feature in the inventory.

The map is a matrix with feature numbers on one axis and test layers on the other. The four layers are: feature spec (this document), Gherkin scenario (Phase 2 output), E2E test (Phase 2 execution), and unit test (Phase 3 scope). Each cell contains one of four states: covered, gap, partial, or not-applicable. "Partial" means coverage exists but does not match the spec — for example, `app.component.spec.ts` tests polling lifecycle (4 cases) but does not test the status bar states that polling drives.

The map also records the existing infrastructure per layer. For unit tests: Karma 6.4.0 config, ChromeHeadlessCI browser, two service mocks, one component spec file. For E2E: pytest-bdd 7.0, Playwright 1.44, five feature files covering backend flows, one page object, session fixtures for Flask and Angular servers. For Gherkin: the same five feature files, which are backend-only and do not cover the overview page. For feature specs: this document, which is being created by this phase.

The gap list extracted from this matrix becomes the scope input for Phases 2 and 3. Phase 2 picks up every feature where the Gherkin and E2E columns show "gap." Phase 3 picks up every feature where the unit test column shows "gap" or "partial."

### Component 4: Unit Test Audit (Task 5)

**Purpose**: Cross-reference the 146 existing unit tests against the new feature specs to determine which tests verify spec-defined behavior and which are orphaned implementation tests.

The audit classifies each existing test into one of three buckets. "Aligned" means the test verifies a behavior described in a feature spec — the test's assertion matches a row in some spec's state matrix. "Misaligned" means the test verifies a behavior that exists but the test's expectation disagrees with the spec — these are the dangerous ones, because they pass today but enforce the wrong contract. "Orphaned" means the test verifies an implementation detail that no spec covers — helper function internals, intermediate computation steps, or behaviors that were refactored away.

The output is a reconciliation punch list: which tests to keep as-is, which to update to match the spec, and which to retire. This list feeds directly into Phase 3's rework scope.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Spec format | Markdown with structured headings and decision tables | Consumed by humans (Sam) and by the Phase 2 Gherkin generation pipeline. Markdown is already the native format for all spec-doc deliverables. No tooling dependency. |
| Feature discovery | Manual codebase scan of `web-ng/src/app/` and `data/projects/*/implementation-guide.md` | No automated scanner — per epic scope, this is a manual inventory task. The scan targets are well-defined: templates, components, routes, services, interceptors, state, and styles. |
| Coverage matrix | Markdown table in the same document | A separate spreadsheet or database would violate the single-document deliverable constraint. The matrix is small enough (roughly 25 features × 4 layers) to fit in a table. |
| Test layer: unit | Karma 6.4.0 + Jasmine 5.4.0 (existing) | Already configured in `web-ng/karma.conf.js` with ChromeHeadlessCI. No reason to migrate — the existing setup works and Phase 3 will extend it. |
| Test layer: E2E | pytest-bdd 7.0 + Playwright 1.44 (existing) | Already configured in `e2e/conftest.py` with Flask and Angular server fixtures. Phase 2 extends this with new feature files. |
| Mock boundary | `CHAIN_PROVIDER=mock` (existing adapter) | The chain adapter's mock provider returns deterministic fixture output. All specs that touch AI behavior define expectations against mock output, not real AI responses. |
| Billing mock boundary | Fixture-based SubscriptionService mock | No real Stripe calls. Specs define the `plan()` signal value and `usageRemaining` signal value as test inputs. The billing interceptor specs define which HTTP headers the mock server returns. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Retire the F1–F17 numbering and assign new domain-prefixed identifiers (OV-, SA-) | The draft numbering was created before Phase 2a/2b shipped. At least 8 new features (isolation, billing, upgrade page, usage meter, billing interceptor, lapsed state, auto-migration, access denied UI) have no numbers. Re-using F18, F19, etc. would create a flat list mixing unrelated domains. Domain prefixes make the inventory scannable and allow insertion without renumbering. | Any existing references to F1–F17 in notes or conversations become stale. This is acceptable because no downstream artifact (test, Gherkin file, CI config) references these numbers — they existed only in the braindump. |
| Single document rather than one file per feature | The total feature count is roughly 25–30. At one file per feature, the directory would contain 30 markdown files with no structural relationship visible at the filesystem level. A single document with a rigid heading structure is navigable via outline, searchable via text, and diffable via git. The document stays under the spec-doc convention of one deliverable per phase. | The file will be long (estimated 800–1200 lines), violating the P7 200-line guideline. This is a documentation artifact, not a code module — the guideline exists to prevent god-files in source code, not to fragment specification documents that must be read as a coherent whole. |
| State matrix format instead of prose descriptions for expected behavior | Prose descriptions ("when the user is logged in and has a Pro plan, the upgrade button is hidden") are ambiguous about completeness — the reader cannot tell whether all combinations have been covered. A decision table with one row per input combination makes gaps visible by their absence. Phase 2 can generate one Gherkin scenario per row mechanically. | Decision tables are harder to write and require the spec author to enumerate combinations explicitly. For features with many input dimensions (e.g., the billing interceptor handles 429 × plan × feature combinations), the table can grow large. The trade-off is worthwhile because the alternative — discovering missing combinations during test authoring — is more expensive. |
| Specs define mock boundary annotations rather than assuming mock compatibility | Some features depend on external services (Stripe billing, JWT validation) that the mock chain provider does not cover. Without explicit mock boundary annotations, Phase 2 authors would discover untestable specs only when writing tests. By annotating each spec with what the mock provides, the spec document itself becomes the testability contract. | Adds a section to every spec that involves an external dependency. For pure-UI features (masthead, dark mode, grid layout), the mock boundary is "none" and the section is trivially short. The overhead is concentrated on the 8–10 features that touch auth, billing, or AI — exactly the features where testability is most at risk. |
| Treat `billing_status()` lapsed→free mapping as a known divergence, spec against the UI tri-state | The OpenAPI `Plan` enum has two values (free, pro) but the UI has three states (free, pro, lapsed). The `billing_status()` route maps lapsed→free for API consumers. The feature specs define behavior against the UI tri-state because that is what the user sees and what tests verify. A divergence note in the billing specs documents the mapping so that future OpenAPI updates do not silently break the UI contract. | If someone reads only the OpenAPI spec, they will not know that "free" can mean "never paid" or "payment failed." The divergence note mitigates this but does not eliminate it. Resolving the divergence (adding "lapsed" to the OpenAPI enum) is out of scope for this phase — it is a backend API change that belongs in a future billing epic. |
| Discovery scans impl guides from all ten epic branches, not just the codebase | The codebase shows what exists now but not what was intentionally shipped. An impl guide might document a feature that was later refactored into a different component — scanning only the codebase would miss the original intent and might not recognize the refactored version as the same feature. Conversely, an impl guide might document a feature that was planned but not merged — scanning only impl guides would produce phantom specs. Using both inputs and cross-referencing catches both failure modes. | Doubles the discovery effort compared to scanning only one source. For ten epic branches with impl guides averaging 200–400 lines, this adds roughly 3000 lines of reading. The cost is a few hours of Task 1 time, which is budgeted at one full day. |
| Coverage matrix uses four states (covered, gap, partial, not-applicable) rather than binary | Binary (tested / not tested) does not capture the most dangerous situation: a test exists but does not match the spec. The "partial" state flags features where coverage exists but is incomplete or misaligned — these are higher priority than pure gaps because they create false confidence. "Not-applicable" handles features that cannot be meaningfully tested at a given layer (e.g., CSS typography decisions cannot be unit-tested). | Four states require judgment calls during the audit. "Partial" vs "covered" is subjective — how complete must coverage be to qualify as "covered"? The decision rule: "covered" means every row in the spec's state matrix has a corresponding test assertion. Anything less is "partial." This makes the classification mechanical once the spec exists. |

## Integration Points

### Upstream: Codebase and Implementation Records

Task 1 reads from two source categories. The live codebase under `web-ng/src/app/` provides the current state of templates, components, services, interceptors, and styles. The implementation records under `data/projects/` for each of the ten executed epic branches provide the shipped-feature narrative. The discovery process cross-references these to produce the verified inventory. Files that exist in code but appear in no impl guide are flagged for investigation — they may be scaffolding, dead code, or undocumented features.

### Downstream: Phase 2 (Gherkin + E2E) and Phase 3 (Unit Tests)

The feature spec document is the sole input to Phase 2 scenario authoring. Each spec's state matrix generates Gherkin scenarios. Each spec's mock boundary annotation tells Phase 2 what fixtures to prepare. The stable feature numbering (OV-xx, SA-xx) becomes the traceability key — every Gherkin feature file references its spec number, every unit test file references its spec number. When a spec changes, grep for the spec number finds every downstream artifact that needs updating.

### Lateral: Product Behavior Contract

The existing `product-behavior.md` documents five core flows that map 1:1 to the five E2E feature files. The feature specs are a superset — they cover the same five flows plus twenty additional features. The architecture does not replace `product-behavior.md` but does note where the two documents overlap, so that future updates maintain consistency. Per the CLAUDE.md rule, any flow change must be reflected in both `product-behavior.md` and its corresponding E2E feature file. The feature specs add a third synchronization point for the overlapping flows.

### Mock Provider Boundaries

Features fall into three testability tiers based on their external dependencies. Tier 1 (pure UI) features — masthead, grid layout, dark mode, section navigation — have no external dependencies and are testable with Karma alone. Tier 2 (mock-covered) features — project listing, polling, teaser generation, section taxonomy — depend on `ProjectsService` data that the existing `projects.service.mock.ts` provides. Tier 3 (fixture-required) features — auth gate, billing interceptor, upgrade page states, usage meter, access denied UI — require test fixtures for JWT tokens, Stripe responses, and HTTP headers that do not yet exist. The spec document flags every Tier 3 feature with the specific fixture it needs, giving Phase 2 a concrete preparation list.

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Draft inventory misses shipped features, producing incomplete specs | High — ten epic branches shipped over three months with no central feature registry | Task 1 scans both codebase files and all ten impl guides. Cross-referencing catches features present in code but absent from the draft, and vice versa. The task is budgeted at a full day to allow thorough scanning. |
| Feature behavior has diverged between impl guide intent and actual code | Medium — solo dev shipping fast across five projects | Specs are written against the live codebase, not the impl guides. Impl guides inform discovery (what was shipped) but the code is the behavioral authority. Where the two disagree, the spec documents the code's behavior and adds a divergence note. |
| Spec format is too rigid for features with qualitative behavior (typography, spacing) | Medium — 14 UX decisions in the braindump involve CSS values | Visual/CSS features get a simplified spec format: summary, the CSS rule or value that encodes the decision, and the selector or component that applies it. These specs are not state-matrix candidates — they map to visual regression tests (out of scope) or to DOM-assertion E2E tests (Phase 2) that check for the presence of a CSS class or computed style. |
| Numbering scheme breaks when features are added in future epics | Low — domain prefixes and monotonic numbering within each domain allow insertion | New features get the next available number in their domain prefix. Existing numbers never change. If a feature is removed, its number is retired, not reused. This is the same scheme used by RFCs and works at much larger scales. |
| The 146 existing unit tests are too tangled to audit against specs | Low — Phase 3 already organized tests by service module | The audit (Task 5) is scoped as a classification exercise, not a rewrite. Each test gets one label (aligned, misaligned, orphaned). The reconciliation punch list is Phase 3's problem. If classification is ambiguous, the test is marked "misaligned" — the conservative choice that triggers review rather than silent acceptance. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving this phase: absence of feature-level specifications, tests mirroring code rather than intent, no coverage visibility
- [Epic](./epic.md) – Scope, five tasks, success criteria, and effort estimates
- [Timeline](./timeline.md) – Status tracking for Tasks 1–5