# Test Phase 3: Unit & Component Tests

## What this is

Karma/Jasmine unit tests for pure logic (services) and component tests for DOM rendering + signal reactivity. These change more often than E2E tests because they're coupled to implementation. They catch regressions faster and run in milliseconds without spinning up servers.

**Depends on:** Phase 1 feature specs (test cases derived from F10, F11 especially), Phase 2 Gherkin (behavioral coverage gaps filled by unit tests).

---

## Existing Unit Tests

`web-ng/src/app/app.component.spec.ts` — 4 test cases:
1. Component creation smoke test
2. Polling stops after POLL_MAX_RETRIES
3. pollingError signal set after max retries
4. pollTimer cleared on ngOnDestroy

Mock infrastructure:
- `projects.service.mock.ts` — `createProjectsServiceMock()` returns jasmine SpyObj
- `ai.service.mock.ts` — `createAiServiceMock()` returns jasmine SpyObj

---

## Pure Function Unit Tests

Highest value per effort. No DOM, no async, no TestBed. Just import the function and assert outputs.

### section-taxonomy.service.spec.ts (F10)

Tests for `sectionFor(project, hasActiveJob)`:

```
describe('sectionFor', () => {
  // Active takes precedence over file state
  - project with hasActiveJob=true → 'Active'
  - project with hasActiveJob=true and implementation-guide.md → 'Active' (job wins)

  // File-based classification
  - project with implementation-guide.md → 'Specced'
  - project with architecture.md → 'Ready to build'
  - project with epic.md → 'Ready to build'
  - project with architecture.md AND epic.md → 'Ready to build'
  - project with braindump.md only → 'Braindumps'
  - project with empty specs array → 'Braindumps'

  // Archive
  - project with archived=true → 'Archive'
  - project with archived=true and implementation-guide.md → 'Archive' (archived wins)
});
```

```
describe('SECTION_ORDER', () => {
  - contains exactly 5 sections
  - order is: Active, Ready to build, Specced, Braindumps, Archive
});
```

### project-teaser.spec.ts (F11)

Tests for `firstNonHeadingSentence(content)`:

```
describe('firstNonHeadingSentence', () => {
  - empty string → ''
  - only whitespace → ''
  - only headers ('# Title\n## Subtitle') → ''
  - only bullet lines ('- item\n- item') → ''
  - only blockquote lines ('> quote') → ''
  - only table lines ('| col |') → ''
  - sentence after header ('# Title\nThis is content.') → 'This is content.'
  - sentence with exclamation ('Watch out!') → 'Watch out!'
  - sentence with question ('Is this working?') → 'Is this working?'
  - multi-sentence paragraph → returns first sentence only
  - line > 120 chars without sentence boundary → truncated + '…'
  - line exactly 120 chars → no truncation
  - mixed: headers, bullets, then prose → returns the prose sentence
  - code block content (backticks) → treated as regular line (not skipped)
});
```

Tests for `countTasks(content)`:

```
describe('countTasks', () => {
  - no ## Task headings → 0
  - one ## Task heading → 1
  - three ## Task headings → 3
  - ## TaskExtra (no space boundary) → still counts (regex is ^## Task)
  - ### Task (h3, not h2) → 0
  - ## Task in middle of content → counts correctly
});
```

Tests for `projectTeaser(section, activeStep, leadFileContent, taskCount, archivedAt)`:

```
describe('projectTeaser', () => {
  // Active section
  - Active + step 'architecture' → 'generating architecture…'
  - Active + no step + content → first sentence from content
  - Active + no step + no content → ''

  // Specced section
  - Specced + taskCount 5 → 'Implementation guide ready · 5 tasks'
  - Specced + taskCount 1 → 'Implementation guide ready · 1 task' (singular)
  - Specced + taskCount 0 + content → first sentence
  - Specced + no taskCount + no content → ''

  // Ready to build
  - Ready to build + content → first sentence
  - Ready to build + no content → 'Ready to build'

  // Braindumps
  - Braindumps + content → first sentence
  - Braindumps + no content → 'Braindump — ready to generate'

  // Archive
  - Archive + valid date string → 'Archived May 12, 2026'
  - Archive + invalid date → 'Archived {raw string}'
  - Archive + no date → 'Archived'

  // Fallback
  - unknown section + no data → ''
});
```

---

## Component / Template Tests

Extend `app.component.spec.ts` with template rendering tests. These need TestBed but use the existing mock infrastructure.

### Masthead tests (F2)

```
describe('masthead', () => {
  - renders "Specview" title in .masthead-title
  - renders today's date in .masthead-date
  - renders "All the Specs Fit to Read" tagline
  - renders "+ New" button
  - renders theme toggle button
  - renders "Sign out" button
});
```

### Section navigation tests (F3)

```
describe('section nav', () => {
  - renders 7 section tabs (Context, All, Active, Ready to build, Specced, Braindumps, Archive)
  - "All" tab is active by default
  - clicking a tab updates activeSection signal
  - count badges render with correct numbers from sectionCounts()
  - clicking "Context" hides search bar and shows context grid
});
```

### Status bar tests (F4)

```
describe('status bar', () => {
  - idle mode: renders "specview · idle — ready"
  - idle mode: has .gen-status-bar--idle class
  - active mode: renders project name and step
  - active mode: has .gen-status-bar--active class
  - active mode: renders .gen-status-track (shimmer container)
  - success mode: renders "done"
  - failure mode: renders error message and retry button
  - retry button calls retryLastOp()
});
```

### Search tests (F5)

```
describe('search', () => {
  - renders search input
  - typing updates searchQuery signal
  - count shows "N projects" when no query
  - count shows "N matches" when filtering
  - search bar hidden when activeSection is 'context'
  - empty filteredProjects shows empty state message
});
```

### Grid tests (F6, F7, F8, F9)

```
describe('all-sections grid', () => {
  - renders .section-group for each non-empty section
  - section groups appear in canonical order (Active → Ready to build → Specced → Braindumps)
  - each section group has .section-group-title with section name
  - Active section has .hero-grid class
  - first card in each section has .featured class
  - cards render project name in .file-item-title
  - cards render teaser in .file-item-teaser
  - cards render file count in .badge
  - clicking a card calls selectProject with correct ID
});

describe('single-section view', () => {
  - renders .file-column elements (3 columns)
  - first column has header with section label + count
  - projects distributed across columns
});
```

### Auth gate tests (F1)

```
describe('auth gate', () => {
  - when isLoggedIn is false: renders app-login component
  - when isLoggedIn is false: does not render .page div
  - when isLoggedIn is true: renders .page div
  - when isLoggedIn is true: does not render app-login
});
```

### Dark mode tests (F16)

```
describe('dark mode', () => {
  - isDark false: renders ☾ icon
  - isDark true: renders ☀ icon
  - clicking toggle calls toggleTheme()
});
```

---

## CI Integration

Add `ng test` to the CI pipeline so frontend tests run on every PR:

```yaml
# .github/workflows/ci.yml
jobs:
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd web-ng && npm ci
      - run: cd web-ng && npx ng test --watch=false --browsers=ChromeHeadless --code-coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: web-ng/coverage/
```

`karma.conf.js` already has `ChromeHeadlessCI` configuration. The `--browsers=ChromeHeadless` flag activates it.

---

## What's Explicitly Not in This Phase

- **Project detail page tests** — editor, text ops, diff view, file sidebar. That's a separate phase.
- **Visual regression** — Playwright screenshots. Stretch goal after E2E is stable.
- **Integration tests** — testing real HTTP calls to the API. The E2E tests in Phase 2 cover this via Playwright.
- **Projects.service.spec.ts** — HTTP service tests with `HttpClientTestingModule`. Useful but lower priority than pure function tests and template tests.
