# 🏗️ Solution Architecture: Gherkin Feature Files

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The testing layer introduced in Task 3 — page objects and a shared fixture — created the structural vocabulary for describing application behaviour, but left that vocabulary unspoken. Gherkin feature files are the sentences. Each `.feature` file translates one named user flow into a machine-executable contract written in plain language. The architecture here is deliberately thin: the primary design challenge is not what to build but how to wire three existing pieces together — Gherkin scenario text, pytest-bdd step bindings, and Task 3's page object methods — without letting any one piece do the other's job.

The guiding insight is separation of authoring from binding. Gherkin scenarios are written against observed UI behaviour and express intent in business terms. Step functions are the translation layer that maps intent to page object calls. Page objects own the selector knowledge. This three-layer separation means a scenario can be reviewed and reasoned about before a single line of Python is written, and a step binding can change without touching the scenario that invoked it. The two are independently correctable, which matters in a solo workflow where there is no reviewer to catch a conflated concern before it ships.

Five feature files map directly to the five critical user flows identified in the analysis. This is a fixed scope — not a starting point for discovery. The architecture imposes no abstraction beyond what those five flows require: no shared step library, no base classes, no shared step registry. One concrete consumer per step module; no premature generalisation.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| One concrete consumer per component | Each step-definition module exists solely to back one `.feature` file — no shared step library is designed because no second consumer is named in the epic |
| Authoring before binding | Scenario text is authored and reviewable in isolation; step functions are written after, bound explicitly to the scenario's vocabulary |
| Green or skip, never silent | Every scenario must terminate in a verifiable state: passing or explicitly marked with a non-empty `reason` string — ambiguity about test state is a failure mode |
| Page objects own selectors | Step functions call page object methods; they never query the DOM directly — selector knowledge does not leak across the boundary |
| Port budget as a constraint | The 15-step-function ceiling and the no-new-page-object rule are architectural constraints, not style preferences — they prevent scope from absorbing adjacent concerns |

---

## System Boundaries

### What This System Includes

- Five Gherkin `.feature` files, one per named flow, containing complete Given/When/Then scenarios authored against current UI behaviour
- Five pytest-bdd step-definition modules, one per feature file, binding scenario steps to Task 3 page object methods and the shared fixture
- A green-or-documented-skip gate that verifies every scenario terminates in a known, committed state before the epic closes

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Shared step library or base step class | Only one consumer per step module exists in this epic; extracting shared steps is the abstraction of one concrete case — it belongs when a second feature file reuses the same vocabulary |
| New page object classes | The epic names five flows and Task 3 named those page objects; a net-new class implies a net-new flow, which is scope creep |
| CI pipeline integration | GitHub Actions wiring is a separate capability; no workflow files change here — trigger condition for re-scoping is when the green gate needs to run automatically on every PR |
| New `data-test` attributes or UI component changes | Missing selectors surface a gap in Task 3's page objects, not a requirement to modify the application under test |
| `xfail` markers without reason strings | Silent failure acceptance masks real breakage; the architecture treats an unexplained skip identically to a test gap |

---

## Component Design

### Gherkin Feature Files

**Purpose**: Capture the intent of each user flow in business-readable language that is independent of any Python implementation detail. These are the contracts that step functions must satisfy.

**Key Parts**:
- `bootstrap-happy.feature` — scenarios for the successful project bootstrap path: brain dump input, doc generation, project appearance in the sidebar; consumed by the bootstrap-happy step module in Task 2
- `bootstrap-fail-fast.feature` — scenarios for validation failure and error surfacing before generation begins; consumed by the bootstrap-fail-fast step module in Task 2
- `edit-spec.feature` — scenarios for loading a project, editing a spec file, and observing auto-save behaviour; consumed by the edit-spec step module in Task 2
- `context-editor.feature` — scenarios for entering and persisting context editor input across the relevant UI states; consumed by the context-editor step module in Task 2
- `rewrite-operation.feature` — scenarios for triggering an AI rewrite operation and observing the transformed output; consumed by the rewrite-operation step module in Task 2

**Patterns**: Each file is authored in Given/When/Then form with concrete, observable state — no conditional branches inside a scenario, no nested steps. Scenario titles follow the `condition_expectedOutcome` convention established in the architecture principles.

### pytest-bdd Step-Definition Modules

**Purpose**: Translate Gherkin step text into calls against Task 3's page object interface and shared fixture. These are the binding layer — they neither own selectors nor encode business intent, only the mapping between the two.

**Key Parts**:
- `steps_bootstrap_happy.py` — binds the bootstrap-happy feature's steps to `BootstrapPageObject` methods and the shared fixture; the only consumer of the bootstrap-happy feature file
- `steps_bootstrap_fail_fast.py` — binds the fail-fast validation steps to the same page object at its error-state surface
- `steps_edit_spec.py` — binds the editor flow steps to `EditorPageObject` and auto-save fixture state
- `steps_context_editor.py` — binds context panel steps to the context editor page object surface from Task 3
- `steps_rewrite_operation.py` — binds rewrite trigger and result-observation steps to the rewrite-capable page object surface

**Patterns**: Each module registers steps using the pytest-bdd `@given`, `@when`, `@then` decorators, delegating immediately to the page object — no assertion logic or DOM queries inside step functions. Any selector gap discovered during authoring triggers a targeted extension to the existing Task 3 page object, documented in the commit body as a deviation.

### Green-or-Skip Gate

**Purpose**: Enforce that every scenario reaches a known, documented terminal state before the epic closes — no scenario is left in an ambiguous passing-by-accident or silently-ignored state.

**Key Parts**:
- Explicit `pytest.mark.skip(reason="...")` markers on any scenario whose environment dependency (live backend, network) cannot be satisfied in the test context — the reason string is committed alongside the marker, not added post-hoc
- The final run of the full suite produces output where every scenario is either green or identified by name with its skip reason — this output is the acceptance signal for Task 3 of the epic

**Patterns**: Skip-over-xfail is a deliberate choice: `xfail` implies expected failure is a normal state; `skip` with a reason implies the scenario is valid but its preconditions are currently unmet. The distinction keeps the suite honest about what is tested versus what is deferred.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Scenario language | Gherkin (`.feature` files) | Human-readable contracts that separate intent from implementation; readable without Python knowledge |
| Test runner | pytest | Already the project standard from Task 3; no new test runner dependency |
| BDD binding | pytest-bdd | Integrates Gherkin parsing with pytest's fixture and marker system; no subprocess or separate runner needed |
| Page object layer | Task 3 page objects (existing) | Selector ownership stays where it was established; step functions delegate rather than duplicate |
| Shared fixture | Task 3 shared fixture (existing) | Application boot and teardown are already handled; importing rather than re-implementing is the correct boundary |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| One step module per feature file, no shared registry | The epic names five distinct flows with no stated shared vocabulary; a shared registry is the abstraction of one concrete case and calibrated by no real reuse yet | If two feature files eventually share step text, a shared module is cheap to extract at that point — building it now locks in a shape before the pull exists |
| Authoring (Task 1) separated from binding (Task 2) | Scenario intent can be reviewed and corrected before binding logic is written; conflating them means a poorly-scoped scenario is harder to see because it is already half-implemented | Adds an explicit handoff step; acceptable because the port budget is small and solo review benefits from the forced pause |
| Skip over xfail for environment-constrained scenarios | Skip is an honest signal that the scenario is valid but preconditions are unmet; xfail allows silent green on unexpected pass and obscures what the suite actually exercises | Skip markers must carry explicit reasons or they are indistinguishable from laziness — the architecture enforces this as a hard rule, not a style suggestion |
| Page object extension permitted, new classes not | Selector gaps during step authoring are Task 3 gaps, not new flows; a single targeted method is the minimal correction — a new class implies a new flow that is out of scope | If a flow requires a page object so structurally different from Task 3's that extension is untenable, the epic has a Task 3 defect to surface, not a reason to introduce new abstractions here |
| Port budget as an architectural constraint | 15 step functions across five modules forces scenario discipline — each step must earn its existence; unconstrained step growth is a signal that scenarios have become implementation tests rather than flow tests | The ceiling is approximate, not absolute; the real signal is whether step count growth tracks scenario count growth linearly |

---

## Patterns

### Delegate-Only Step Functions

**When to use**: Every step function in every module — no exceptions.

**How it works**: A step function receives fixture-provided context and calls exactly one page object method. It does not query the DOM, does not assert directly against raw HTML, and does not embed wait loops. The page object already encodes the right selector and wait strategy; duplicating that knowledge in the step function creates two places to update when a selector changes.

**Example**: A `when` step for clicking "Bootstrap" calls the bootstrap page object's trigger method — the step function is a named pass-through, not an implementation.

### Scenario-Per-Flow, Not Scenario-Per-State

**When to use**: Authoring the feature files in Task 1.

**How it works**: Each scenario describes a complete user journey through one named flow, from a known starting state to a verifiable end state. Scenarios are not unit tests of individual UI states — they are flow tests. A scenario that exercises only one interaction in isolation belongs in a page object test, not a feature file.

**Example**: The bootstrap-happy scenario starts with an empty project list, inputs a brain dump, triggers generation, and verifies the project appears in the sidebar — the full arc, not just the click.

### Skip-With-Reason as First-Class Output

**When to use**: Any scenario whose environment preconditions (live backend, external network, real AI response) cannot be reliably satisfied in the test context.

**How it works**: The skip marker and its reason string are committed alongside the scenario in the same commit — not added as a cleanup step later. The reason string names the specific precondition that is unmet and the condition under which the skip should be removed. This turns the skip into a deferred task with a trigger, not a permanent exemption.

**Example**: A rewrite-operation scenario that requires a live Claude API response carries a skip reason naming the dependency and the condition — "requires live Anthropic API; re-enable when test environment provisions credentials" — committed in Task 3 of the epic.

---

## Execution Flow

```
[Phase 1 — Authoring]
  Task 1: Write .feature files
    │  (scenario intent reviewable before binding)
    ▼
[Phase 2 — Binding]
  Task 2: Implement step modules
    │  (page object extensions documented as deviations)
    ▼
[Phase 3 — Convergence]
  Task 3: Drive to green or documented skip
    │  (zero net-new code; only skip markers and step corrections)
    ▼
  Green-or-skip gate passes → epic closes
```

The three phases are strictly sequential within this epic. Task 1 must be committed and reviewable before Task 2 begins — the separation is the mechanism by which scenario intent is validated before it becomes expensive to change. Task 3 is a convergence phase only: its output is skip markers and step corrections, not new code. Any pressure to introduce new step functions or new page object methods in Task 3 is a signal that Task 2 was underspecified, which surfaces as a deviation to document rather than silently absorb.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview