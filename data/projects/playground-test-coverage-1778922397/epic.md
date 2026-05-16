# 🎯 Epic: Playground & V2 Test Coverage

## Business Value

The spec-doc frontend carries 1,087 lines of untested orchestration logic in `app-v2.component` and 1,760+ lines across six playground components with zero automated coverage. V3's planned extraction of state into `AppStateService` is the riskiest refactor on the roadmap—it touches every signal, every computed value, every user-facing flow. Without a pre-extraction test suite, there is no mechanized way to prove V3 didn't regress behavior. Every bug that slips through becomes a production incident on humaniz.me or a silent data-loss scenario in the spec editor.

Writing these tests now—before the extraction branch forks—converts a high-risk refactor into a safe, verifiable operation. The 135 new assertions become a contract: if `ng test` stays green after extraction, the migration is correct. This is the difference between "I think it still works" and "CI proves it still works."

For a solo founder shipping across five active projects, automated regression coverage is the only scalable substitute for a QA team. Each hour invested here saves multiple hours of manual verification on every future change to the workspace UI.

## Scope

### What This Epic Covers

- **Playground leaf component specs** – Unit tests for `pg-tokens`, `pg-animations`, `pg-borders`, and the `css-read.util` helper that underpins token reading
- **Playground complex component specs** – Tests for `pg-state-matrix` (demo data rendering, sanitization) and `live-playground` (orchestration, signal wiring, shallow-rendered composition)
- **App-v2 pre-V3 regression suite** – 48 tests targeting signals, computed values, methods, polling lifecycle, and bootstrap pipeline on the existing component, structured for trivial 1:1 migration to `AppStateService`
- **App-v2 basic behavior tests** – 15 tests covering service injection, conditional rendering, and navigation delegation

### What This Epic Does NOT Cover

- ❌ **V3 extraction itself** — This epic builds the safety net, not performs the surgery
- ❌ **landing-pitch.component** — Pure presentational (481 lines, zero logic); re-scope only if interactivity is added
- ❌ **playground-demo-data standalone spec** — Data shape validated implicitly by state-matrix tests
- ❌ **pg-components-app / pg-components-ui** — Unknown line counts, no test design provided; deferred to follow-up after line audit
- ❌ **Integration or E2E tests** — Scope is unit-level only (Jasmine + TestBed)
- ❌ **Refactoring any component under test** — Tests assert current behavior as-is

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Utility & leaf specs** (`css-read.util`, `pg-borders`, `pg-tokens`, `pg-animations`) | None | — | 1.5 days | High |
| 2 | **State-matrix & live-playground specs** | Task 1 (child specs must exist for failure attribution) | — | 2 days | High |
| 3 | **App-v2 pre-V3 regression suite** (signals, computed, methods, polling, bootstrap) | None | With Task 1–2 | 2 days | High |
| 4 | **App-v2 basic behavior tests** (injection, rendering, navigation) | None | With Task 3 | 0.5 days | High |
| 5 | **CI gate verification & coverage audit** | Tasks 1–4 | — | 0.5 days | Low |

## Success Criteria

- ✅ Every playground component (`pg-tokens`, `pg-animations`, `pg-state-matrix`, `live-playground`, `pg-borders`) has a `.spec.ts` file with ≥ 5 passing tests
- ✅ `css-read.util.spec.ts` exists and covers the graceful-empty-value path
- ✅ `app-v2.component.spec.ts` contains ≥ 48 tests structured as `component.x()` assertions (migration-ready)
- ✅ MutationObserver lifecycle (setup + teardown) covered in `pg-tokens` spec
- ✅ Replay reflow trick (`void el.offsetWidth`) covered in `pg-animations` spec
- ✅ `ng test` passes with **≥ 390 total tests** (257 existing + 135 new)
- ✅ `ng build --configuration production` passes
- ✅ Zero regressions in existing 257 tests (no modifications to existing spec files)
- ✅ All app-v2 pre-V3 tests use mock services exclusively—no real HTTP, no real localStorage

## Related Documents

- [Analysis](./analysis.md) – Coverage audit and gap identification driving this epic
- [Solution Architecture](./architecture.md) – Mock strategy, shallow-rendering approach, and test migration pattern
- [Timeline](./timeline.md) – Task completion tracking and V3 branch-fork gate
---

## Implementation Notes

1. **Include pg-components-app + pg-components-ui.** Both exist (30 + 63 lines), survive V3. Add ~18 tests. Total target: ~410.
2. **Exclude landing-pitch.** 12 lines, zero logic. Not worth a spec file.
3. **Success criteria: ≥ 410 total tests** (257 existing + ~153 new), not 390.
4. **Flat file paths.** All spec files at `web-ng/src/app/` level per CLAUDE.md.
5. **Test names: present tense, no "should".** `it('creates')` not `it('should create')`.
