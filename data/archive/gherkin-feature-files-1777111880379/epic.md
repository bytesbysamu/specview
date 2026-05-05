# 🎯 Epic: Gherkin Feature Files

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Task 3 shipped page objects and a shared fixture — the selector and setup infrastructure for integration testing — but left no executable scenarios. That gap means any regression across the five core flows (bootstrap-happy, bootstrap-fail-fast, edit-spec, context-editor, rewrite-operation) is caught by hand, after the fact. Gherkin `.feature` files close that gap by turning page object methods into verifiable, machine-executable contracts against real application behaviour.

For a solo founder, a broken flow discovered post-deploy costs more to diagnose than the time spent writing the test. Gherkin scenarios also serve as living documentation: the files are readable by anyone who needs to understand what the application is supposed to do, without reading code. Each scenario that reaches green is a regression fence that runs on every future change without additional effort.

The five flows covered represent the complete user-facing surface of the MVP. Green coverage across all five means any feature branch that breaks a core path is caught before merge — removing the manual smoke-test loop that currently sits between commit and confidence.

**Value Proposition**: Executable scenario coverage over the five critical flows that turns the existing page object investment into a regression fence that runs automatically.

---

## Scope

### What This Epic Covers

- **Gherkin scenario authoring** — five `.feature` files, one per flow, with complete Given/When/Then scenarios written against existing UI behaviour
- **pytest-bdd step implementation** — five step-definition modules binding Gherkin steps to page object methods and the shared fixture from Task 3
- **Green or documented-skip gate** — every scenario either passes or carries an explicit skip reason string before the epic closes

### What This Epic Does NOT Cover

- ❌ **New page objects** — if a selector gap surfaces, the existing page object may be extended; a net-new page object class requires a new capability scope
- ❌ **New UI components** — missing selectors are resolved in the page object layer, not by adding `data-test` attributes to components
- ❌ **CI pipeline integration** — running this suite in GitHub Actions is a separate concern; no workflow changes belong here
- ❌ **Scenario discovery outside the five named flows** — additional user journeys are out of scope; the five flows are fixed by the analysis

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Author Gherkin Scenarios** | Task 3 locked | — | 1 day | High |
| 2 | **Implement Step Functions** | 1 | — | 2 days | High |
| 3 | **Drive Scenarios to Green** | 2 | — | 0.5 days | High |

### Task 1: Author Gherkin Scenarios

Write all five `.feature` files — `bootstrap-happy`, `bootstrap-fail-fast`, `edit-spec`, `context-editor`, `rewrite-operation` — each containing complete Given/When/Then scenarios authored against observed UI behaviour. Scenarios must be self-contained: no step function code, no page object changes, and no assumptions about backend state that the shared fixture cannot provide.

**Port budget**: 5 `.feature` files, scenario text only; no Python code, no page object extensions, no fixture changes — authoring and step-binding are deliberately split so scenario intent can be reviewed before binding logic is written.

### Task 2: Implement Step Functions

Write one pytest-bdd step module per feature file, binding each Gherkin step to the corresponding page object method and shared fixture from Task 3. If a step cannot be bound because a selector is missing, the page object may be extended with a single targeted method — any extension must be documented in the commit body as a deviation. No new page object classes. No new components.

**Port budget**: 5 step-definition modules, ~10–15 step functions total; page object extensions are permitted on confirmed selector gaps only — not preemptively — and new page object files and new UI components are both hard stops.

### Task 3: Drive Scenarios to Green

Run the full scenario suite and resolve failures. Any scenario that cannot reach green due to a genuine environmental constraint (network dependency, live backend required) must carry an explicit `pytest.mark.skip(reason="...")` string — silent skips and `xfail` without a reason are not acceptable. The task closes when every scenario is either green or has a documented skip reason committed alongside it.

**Port budget**: Zero new code expected; the only permitted output is skip markers and, if a step binding was wrong, a correction to a Task 2 step function — no net-new step functions, no page object changes, no feature file rewrites.

---

## Success Criteria

This epic is complete when:

- ✅ All five `.feature` files exist and contain at least one complete Given/When/Then scenario per named flow
- ✅ All five step-definition modules bind every step in their corresponding feature file without unimplemented step errors
- ✅ Every scenario is either green or carries a committed `pytest.mark.skip(reason="...")` with an explicit, non-empty reason string
- ✅ No new page object classes were introduced (page object extension commits, if any, are documented in the deviation log)
- ✅ The step function count does not exceed 15 across all five modules

---

## Non-Goals

- ❌ **CI integration** — scheduling or automating this suite in GitHub Actions is a follow-on capability; no workflow files change here
- ❌ **Scenario coverage beyond the five named flows** — the analysis fixed the scope at five flows; any sixth scenario is scope creep and belongs in a new epic
- ❌ **Page object redesign** — if Task 3's page objects are structurally inadequate for a flow, that is a Task 3 defect to fix in Task 3, not a reason to re-architect here

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview