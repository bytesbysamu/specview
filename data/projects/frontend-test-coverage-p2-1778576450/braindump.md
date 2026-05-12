# Frontend Test Coverage

## What this is

The Angular frontend (`web-ng/`) has zero test coverage. No unit tests, no integration tests, no E2E tests. Before SaaS launch, we need a testing foundation that catches regressions in the core flows: project listing, spec generation pipeline, text operations, and auth.

---

## Current Frontend Architecture

Single-component app with signals (no NgRx, no routing beyond hash-based view switching):

- **`app.component.ts`** — Root component, all state as signals. ~500 lines.
- **`app.component.html`** — Template, ~505 lines. Uses `@if` / `@for` control flow.
- **`services/projects.service.ts`** — All HTTP calls, returns `Promise<T>` via `firstValueFrom()`.
- **`services/section-taxonomy.service.ts`** — Classifies projects into sections (active/specced/braindumps/archive).
- **`services/project-teaser.ts`** — Extracts teaser text from braindump markdown.
- **`api/`** — ng-openapi-gen generated client (auto-generated, don't test directly).
- **`styles.css`** — 1,581 lines, full design system.

---

## Task 1 — Testing Infrastructure Setup

### Test runner
Angular CLI ships with Karma + Jasmine by default. Decide:
- **Option A: Keep Karma/Jasmine** — zero setup, `ng test` just works. Good enough for unit tests.
- **Option B: Switch to Jest** — faster, better DX, but requires migration effort. Worth it if we're writing a lot of tests.

Recommendation: Start with Karma/Jasmine (it's already configured in Angular CLI). Switch to Jest later if pain points emerge.

### First test file
Create `app.component.spec.ts` with a smoke test:
- Component creates successfully
- Signals initialize with expected defaults

### CI integration
- Add `ng test --watch=false --browsers=ChromeHeadless` to CI pipeline
- Fail the build on test failure
- Coverage report with `--code-coverage` flag

---

## Task 2 — Service Unit Tests (Pure Logic, No DOM)

These are the highest-value tests — pure functions with clear inputs/outputs.

### `section-taxonomy.service.spec.ts`

The `sectionFor(project)` function has 5 branches:
1. Project with active/running AI job → `"active"`
2. Project with `implementation-guide.md` in files → `"specced"`
3. Project with `architecture.md` or `epic.md` but no impl guide → `"specced"`
4. Project with `braindump.md` only → `"braindumps"`
5. Archived project → `"archive"`

Test each branch with minimal mock project objects.

### `project-teaser.spec.ts`

The `projectTeaser(project)` and `firstNonHeadingSentence(text)` functions:
- Empty content → returns empty string
- Content with only markdown headers (`# Title\n## Subtitle`) → returns empty string
- Content with a sentence after a header → returns that sentence
- Multi-sentence paragraph → returns only the first sentence
- Content longer than `teaser_chars` → truncated with ellipsis
- Content with code blocks → skips code blocks

### `projects.service.spec.ts`

HTTP service tests using Angular's `HttpClientTestingModule`:
- `loadProjects()` calls `GET /api/projects` with auth header
- `saveFile()` calls `PUT /api/projects/:id/files/:name` with correct body
- `createProject()` calls `POST /api/projects` with name and content
- Error responses (401, 500) are handled correctly
- Auth token is included in all requests

---

## Task 3 — Component Tests (DOM + Signals)

### `app.component` — Overview view
- Renders section tabs (Active, Specced, Braindumps)
- Clicking a tab filters to that section
- Search input filters projects by name
- Project count updates when filter changes
- Status bar shows correct state (idle by default)

### `app.component` — Expanded panel
- Clicking a project card opens the expanded panel
- File nav sidebar lists project files
- Clicking a file loads its content
- Generate button triggers pipeline
- AI ops chips are visible in editor toolbar

### Test approach
Use Angular's `TestBed` with `ComponentFixture`. Mock `ProjectsService` to return canned data. Test signal reactivity by setting signal values and checking DOM updates.

---

## Task 4 — E2E Tests

### Framework choice
- **Cypress** — mature, good DX, but heavy
- **Playwright** — faster, cross-browser, better for CI
- Recommendation: **Playwright** — lighter weight, Angular has first-party support via `@angular/e2e`

### Core flows to cover

**Flow 1: Login**
1. Navigate to app
2. See login form
3. Enter credentials
4. Submit → redirected to project list
5. Auth token stored

**Flow 2: Browse projects**
1. Login
2. See project grid with sections
3. Click section tab → filtered view
4. Type in search → projects filter by name
5. Click project card → expanded panel opens

**Flow 3: Create project**
1. Login
2. Click "New Project" (or equivalent)
3. Enter project name
4. Paste braindump content
5. Project appears in list

**Flow 4: Generate specs**
1. Login
2. Open a project with braindump only
3. Click "Generate" button
4. Status bar shows "generating" state
5. Poll until pipeline completes
6. New files appear (analysis.md, epic.md, architecture.md, timeline.md)
7. Status bar shows "complete"

**Flow 5: Text operations**
1. Login
2. Open a project, select a file
3. Click an AI op chip (e.g., "Expand")
4. Diff view appears with red/green blocks
5. Click "Apply" → file content updated
6. Click "Dismiss" → diff view closes, original content preserved

### Test data
- Seed a test project with known braindump content
- Use mock provider (`CHAIN_PROVIDER=mock`) for deterministic AI responses
- E2E tests run against local docker compose

---

## Task 5 — Visual Regression Tests (Stretch Goal)

The newspaper aesthetic is a core differentiator. Visual regression catches when CSS changes break the design.

- Use Playwright's screenshot comparison
- Capture key states: overview grid, expanded panel, diff view, status bar states
- Compare against baseline screenshots
- Run on PR to catch visual regressions

---

## Priority Order

1. **Testing infrastructure** (Task 1) — unblocks everything else
2. **Service unit tests** (Task 2) — highest value per effort, pure logic
3. **E2E for core flows** (Task 4) — catches integration issues
4. **Component tests** (Task 3) — fills the gap between unit and E2E
5. **Visual regression** (Task 5) — stretch goal, nice to have

---

## Files to Create

| File | Purpose |
|------|---------|
| `web-ng/src/app/app.component.spec.ts` | Component smoke + signal tests |
| `web-ng/src/app/services/section-taxonomy.service.spec.ts` | Section classification logic |
| `web-ng/src/app/services/project-teaser.spec.ts` | Teaser extraction logic |
| `web-ng/src/app/services/projects.service.spec.ts` | HTTP service tests |
| `web-ng/e2e/` | Playwright E2E test directory |
| `web-ng/e2e/login.spec.ts` | Login flow |
| `web-ng/e2e/browse.spec.ts` | Project browsing |
| `web-ng/e2e/generate.spec.ts` | Spec generation pipeline |
| `web-ng/e2e/text-ops.spec.ts` | Text operations + diff view |
| `web-ng/playwright.config.ts` | Playwright configuration |

## Existing CI Reference

The `ci-test-quality` project (`data/projects/ci-test-quality-1778239000/`) already identified the missing test files and some E2E gaps. This project builds on that analysis with a complete implementation plan.
