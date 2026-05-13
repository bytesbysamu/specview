# Implementation Guide: Test Phase 1: Feature Specs & Testing Architecture

## Overview
This epic produces a single specification document that catalogs every user-facing feature of the Specview overview page and SaaS flows, structured as testable specs with stable numbering. Work sequences linearly: Task 1 discovers and inventories all features by scanning the codebase and ten epic branch impl guides, Tasks 2 and 3 write testable specifications for overview-page and SaaS features respectively (parallelizable with each other), Task 4 builds the four-layer testing architecture map from those specs, and Task 5 audits existing unit tests against the new specs to produce a reconciliation punch list for Phase 3. The deliverable is documentation only — no tests are written or modified.

## Shared Pre-flight
- Confirm SaaS Phase 2a/2b branches (PRs #49, #50) are merged and stable in the codebase before beginning Task 3
- Verify access to all ten epic branch project directories under `data/projects/` and confirm each contains an `implementation-guide.md` or `exec-guide-summary.md`
- Verify the live codebase under `web-ng/src/app/` is on the latest merged state with no pending feature branches that would change the overview page surface
- Confirm `CHAIN_PROVIDER=mock` is functional by running the app in mock mode — all specs must be verifiable without live AI or Stripe calls
- Locate existing test infrastructure files: `web-ng/karma.conf.js`, `e2e/conftest.py`, existing E2E feature files, and `projects.service.mock.ts`
- Retire the draft F1–F17 numbering mentally — the new scheme uses domain prefixes `OV-` (overview page) and `SA-` (SaaS/auth), monotonic within each domain
- Identify the target output file path within the spec-doc deliverables directory for the single consolidated specification document
- Review `product-behavior.md` to understand the five existing core flows that overlap with the feature specs and will need consistency notes

---

## Task 1: Feature Discovery & Complete Inventory  [Effort: 1 day]

### What
Scan all ten epic branch implementation guides and the live codebase to produce a verified, numbered catalog of every user-facing feature, replacing the draft F1-F17 list. This inventory becomes the authoritative scope for Tasks 2-5 and the stable numbering system that Phases 2 and 3 reference downstream.

### Files
- **Create**: `data/projects/test-phase1-feature-specs-1778592995/feature-specs.md` — the single deliverable document, starting with the inventory section containing all discovered features organized under OV- and SA- prefixes
- **Modify**: `data/projects/test-phase1-feature-specs-1778592995/timeline.md` — update Task 1 status to in-progress and then complete as the inventory is finalized

### Steps
1. Read every `implementation-guide.md` and `exec-guide-summary.md` across all ten project directories under `data/projects/`, extracting every user-facing feature mentioned as shipped, along with the component or service name associated with it.
2. Scan the live codebase directory `web-ng/src/app/` systematically by file type — templates, components, routes, services, interceptors, and state files — listing every feature-bearing artifact found, such as route guards, page components, service methods that drive UI behavior, and interceptors that alter user flow.
3. Cross-reference the two lists: flag features present in impl guides but absent from the codebase (potential phantom features or refactored artifacts) and features present in the codebase but absent from all impl guides (potential undocumented features or scaffolding).
4. Investigate every flagged discrepancy by reading the relevant source file or impl guide section to determine whether the feature exists, was renamed, was absorbed into another component, or is dead code.
5. Organize verified features into two domains: overview page features (prefix OV-) and SaaS/auth features (prefix SA-), assigning monotonic numbers within each domain.
6. For each inventory entry, record the feature short name, the primary source file path, and a one-sentence scope description sufficient to guide the spec author in Tasks 2-3.
7. Write the completed inventory as the opening section of `feature-specs.md`, with a note that the F1-F17 draft numbering is retired and should not be referenced by downstream phases.

### Verify
- Every feature in the inventory traces to at least one real file under `web-ng/src/app/` — grep each listed primary source file to confirm it exists
- No shipped feature visible in the ten impl guides is absent from the inventory, confirmed by spot-checking three impl guides against the catalog
- The numbering scheme uses OV- and SA- prefixes with no gaps or duplicates, and no references to the old F1-F17 labels remain in the document

---

## Task 2: Overview Page Feature Specs  [Effort: 2 days]

### What
Write testable specifications for every overview-page feature identified in the Task 1 inventory, covering auth gate, masthead, section navigation with badges, status bar states, search and filter, all-sections grid, hero grid, featured card, project cards, section taxonomy, project teasers, single-section view, polling and error recovery, update banner, create modal, dark mode, and context section. Each spec follows the five-section format: summary, inputs, expected outputs, state matrix, and edge cases.

### Files
- **Modify**: `data/projects/test-phase1-feature-specs-1778592995/feature-specs.md` — append the overview page specifications section after the inventory, with one subsection per OV- feature containing summary, inputs, expected outputs, state matrix, and edge cases

### Steps
1. For each OV-prefixed feature in the inventory, read the primary source file and its template to identify every input signal, service dependency, route parameter, and user action that drives the feature's behavior.
2. Write the summary as a single sentence stating what the feature does from the user's perspective, not from an implementation perspective.
3. Document the inputs section by listing every signal, observable, route segment, or DOM event that triggers or parameterizes the feature, using the actual variable and method names from the source code.
4. Define the expected outputs section in terms observable by a test — DOM content, CSS class presence, navigation events, service method calls, or signal value changes — avoiding any reference to internal implementation details that a test harness cannot inspect.
5. Build the state matrix as a decision table with one row per meaningful input combination and its corresponding output, ensuring every combination is explicit and no implicit defaults are assumed.
6. Write at least one edge case per feature addressing what happens when an input is missing, a service call errors, a value is at a boundary, or the user performs an unexpected interaction sequence.
7. For features that depend on ProjectsService data or the mock chain provider, add a mock boundary annotation stating exactly what the mock returns and what the feature does with that return value.
8. For pure-UI features like dark mode, masthead typography, and grid layout, use the simplified spec format: summary, the CSS rule or class that encodes the decision, the selector or component that applies it, and a DOM-assertion-friendly expected output.

### Verify
- Every OV-prefixed feature from the Task 1 inventory has a corresponding spec subsection with all five sections present (summary, inputs, expected outputs, state matrix, edge cases)
- Each state matrix has at least two rows, and each edge cases section has at least one entry
- Every mock-dependent feature (polling, teaser generation, section taxonomy, project listing) includes a mock boundary annotation specifying the fixture data shape
- No spec references a file path, service, or method name that does not exist in the current codebase under `web-ng/src/app/`

---

## Task 3: SaaS & Auth Feature Specs  [Effort: 1.5 days]

### What
Write testable specifications for all SaaS and authentication features identified in the Task 1 inventory, including project isolation (user-scoped listing, 403 access denied UI, dual-write creation, auto-migration), billing (upgrade page free/pro/lapsed states, post-checkout verification, SubscriptionService signals), usage meter, billing interceptor (header reading, 429 routing), and login/register flows. This task can run in parallel with Task 2.

### Files
- **Modify**: `data/projects/test-phase1-feature-specs-1778592995/feature-specs.md` — append the SaaS and auth specifications section after the overview page specs, with one subsection per SA- feature following the same five-section format

### Steps
1. For each SA-prefixed feature in the inventory, read the primary source file, its template, and any associated interceptor or guard to identify all inputs including JWT claims, HTTP headers, Stripe webhook payloads, SubscriptionService signal values, and route parameters.
2. Write the summary for each feature as a single user-facing sentence, being precise about which route or UI state the feature controls.
3. Document the billing features using the UI tri-state contract (free, pro, lapsed) as the testable truth, not the OpenAPI two-value enum, and include a divergence note explaining that `billing_status()` maps lapsed to free for API consumers.
4. Build the state matrix for the upgrade page spec with rows covering every combination of plan status (free, pro, lapsed) and relevant billing signals (usageRemaining, plan expiry), producing the exact UI state each combination renders.
5. For the billing interceptor, enumerate every combination of HTTP response code (especially 429), plan type, and feature context that triggers routing behavior, documenting the header values the interceptor reads and the navigation target it selects.
6. Write the access denied UI spec covering both the 403 response scenario and the ownership-check-failed scenario, documenting what the user sees and what navigation options are available.
7. Add mock boundary annotations for every Tier 3 feature (auth gate, billing interceptor, upgrade page, usage meter, access denied UI), specifying the exact fixture required — JWT token shape, Stripe response fixture, HTTP header values — that Phase 2 must prepare.
8. For login and register flows, document the input validation states, error display conditions, and successful-auth redirect targets, referencing the actual route guard and auth service method names.

### Verify
- Every SA-prefixed feature from the Task 1 inventory has a corresponding spec subsection with all five sections present
- The upgrade page spec's state matrix covers free, pro, and lapsed states, and includes the divergence note about the billing_status() lapsed-to-free mapping
- Every Tier 3 feature (those requiring JWT, Stripe, or HTTP header fixtures) has a mock boundary annotation listing the specific fixture shape needed
- The billing interceptor spec covers the 429 response code routing path explicitly with at least one state matrix row dedicated to it

---

## Task 4: Testing Architecture & Coverage Gap Map  [Effort: 1 day]

### What
Document the four-layer test pyramid (feature specs, Gherkin scenarios, E2E tests, unit tests), catalog existing infrastructure per layer, and build a coverage matrix mapping every feature spec number to its current coverage state across all four layers. The gap list extracted from this matrix becomes the scope input for Phases 2 and 3.

### Files
- **Modify**: `data/projects/test-phase1-feature-specs-1778592995/feature-specs.md` — append the testing architecture section containing the pyramid description, infrastructure catalog, and coverage matrix table
- **Modify**: `data/projects/test-phase1-feature-specs-1778592995/timeline.md` — update Task 4 status as work progresses

### Steps
1. Document the four-layer pyramid structure, defining each layer's purpose: feature specs as the behavioral contract, Gherkin scenarios as the executable specification derived from specs, E2E tests as the Playwright-driven verification of scenarios, and unit tests as the isolated component and service verification.
2. Catalog the existing infrastructure for each layer by reading the actual configuration files: `web-ng/karma.conf.js` for unit test setup (Karma 6.4.0, ChromeHeadlessCI, Jasmine 5.4.0), `e2e/conftest.py` for E2E setup (pytest-bdd 7.0, Playwright 1.44, Flask and Angular server fixtures), existing E2E feature files under the e2e directory, and the mock files like `projects.service.mock.ts`.
3. Build the coverage matrix as a markdown table with every OV- and SA- feature number on rows and the four test layers as columns, assigning each cell one of four states: covered (every state matrix row has a test), partial (some coverage exists but does not match the full spec), gap (no coverage at this layer), or not-applicable (feature cannot be meaningfully tested at this layer).
4. Populate the unit test column by cross-referencing each feature spec against the existing unit test files, checking whether the test assertions correspond to rows in the spec's state matrix.
5. Populate the E2E column by checking the five existing E2E feature files against the feature inventory, noting that existing E2E tests cover backend flows only and the entire frontend interaction surface is a gap.
6. Mark the feature spec column as covered for every feature that has a completed spec from Tasks 2-3, and mark the Gherkin column as gap for all features since no frontend Gherkin scenarios exist yet.
7. Extract the gap list from the matrix: all features where the Gherkin and E2E columns show gap become Phase 2 scope, and all features where the unit test column shows gap or partial become Phase 3 scope.
8. Add a note documenting where the feature specs overlap with `product-behavior.md` and its five core flows, establishing the three-way synchronization requirement for future updates.

### Verify
- The coverage matrix includes every OV- and SA- feature number from the inventory with no features missing
- Each matrix cell contains exactly one of the four defined states: covered, partial, gap, or not-applicable
- The existing infrastructure catalog references real files that exist in the codebase — verify `web-ng/karma.conf.js` and `e2e/conftest.py` are present
- The gap list explicitly names which features are Phase 2 scope (Gherkin + E2E gaps) and which are Phase 3 scope (unit test gaps or partials)

---

## Task 5: Phase 3 Unit Test Audit  [Effort: 0.5 day]

### What
Cross-reference the existing frontend unit tests (155 tests across the Karma suite) and the 819 backend pytest tests against the new feature specs, classifying each test as aligned, misaligned, or orphaned, and producing a reconciliation punch list that tells Phase 3 exactly which tests to keep, update, or retire.

### Files
- **Modify**: `data/projects/test-phase1-feature-specs-1778592995/feature-specs.md` — append the unit test audit section containing the classification table and reconciliation punch list

### Steps
1. List every existing frontend unit test file under `web-ng/src/app/` by scanning for files matching the spec file naming convention (typically `*.spec.ts`), recording the describe block names and individual test case titles.
2. For each test case, read its assertion and determine which feature spec it corresponds to by matching the tested behavior against rows in the state matrices from Tasks 2-3.
3. Classify each test into one of three buckets: aligned (the test assertion matches a specific state matrix row in a feature spec), misaligned (the test verifies behavior that exists but the expectation disagrees with or is narrower than the spec), or orphaned (the test verifies an implementation detail like a helper function internal or intermediate computation that no spec covers).
4. For misaligned tests, note specifically what the test asserts versus what the spec defines as the correct behavior, giving Phase 3 a concrete correction target.
5. For the 819 backend pytest tests, perform a lighter-weight audit: group them by the five existing E2E feature areas, confirm which ones are covered by the E2E feature files, and note any that test behavior now captured by a frontend feature spec (indicating potential redundancy or a testing-layer mismatch).
6. Compile the reconciliation punch list with three sections: tests to keep as-is (aligned), tests to update with the specific spec row they should match (misaligned), and tests to retire with a justification for why the tested behavior is no longer spec-relevant (orphaned).
7. Add a summary count at the top of the audit section showing the total number of tests in each classification bucket for both frontend and backend suites.

### Verify
- Every frontend unit test file found in the codebase appears in the audit classification — no test file is silently skipped
- The classification count totals match the known test counts (155 frontend, 819 backend) or any discrepancy is explained with a note about test count changes since the last measurement
- Every misaligned test entry names both the current assertion and the spec row it should match, providing Phase 3 with an actionable correction
- The reconciliation punch list has all three sections (keep, update, retire) even if some sections are empty, confirming that every classification bucket was addressed