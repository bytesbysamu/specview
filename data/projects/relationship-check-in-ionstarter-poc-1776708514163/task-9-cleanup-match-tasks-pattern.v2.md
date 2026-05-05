# Task 9: Strip Check-In Domain to Match Tasks CRUD Pattern

## 1. Objective

Align the check-in domain (`src/app/domains/check-in/`) with the canonical tasks domain (`src/app/domains/tasks/`) by removing structural noise: rename the routes file, delete dead code, add a pages barrel, fix import styles, and remove redundant decorators.

---

## 2. Scope

| Action | File/Dir |
|--------|----------|
| Rename | `check-in.routes.ts` -> `routes.ts` |
| Delete | `index.ts` (domain root) |
| Delete | `providers/check-in-initializer.ts` + `providers/` dir |
| Create | `pages/index.ts` (barrel export) |
| Edit | `check-in-rating.page.ts` (imports cleanup) |
| Edit | `check-in-submit.page.ts` (imports cleanup) |
| Edit | `check-in-comparison.page.ts` (imports cleanup) |
| Edit | `check-in-trends.page.ts` (imports cleanup) |
| Edit | `../tabs/routes.ts` (update loadChildren path) |

---

## 3. Prerequisites

- Working Angular 19 build (`ng build` passes)
- Familiarity with the tasks domain layout at `src/app/domains/tasks/`
- No open branches editing the same files

---

## 4. Step-by-Step Implementation

### Step 4.1: Rename routes file

Rename `src/app/domains/check-in/check-in.routes.ts` to `src/app/domains/check-in/routes.ts`.

The file contents stay identical. This matches the tasks domain which has `routes.ts` at the domain root.

```bash
git mv src/app/domains/check-in/check-in.routes.ts src/app/domains/check-in/routes.ts
```

### Step 4.2: Update tabs routes reference

In `src/app/domains/tabs/routes.ts`, change the check-in loadChildren import path:

```typescript
// Before
import('../check-in/check-in.routes').then(m => m.routes),

// After
import('../check-in/routes').then(m => m.routes),
```

### Step 4.3: Delete domain root `index.ts`

Delete `src/app/domains/check-in/index.ts`. The tasks domain does not have a root barrel. The only exports in this file are `detectDivergences` and `SustainedDivergenceAlert` from the utils.

**Before deleting**, grep the codebase for any imports from `'../check-in'` or `'../../check-in'` or `'@app/domains/check-in'`. If any exist, update them to import directly from the util file instead:

```bash
grep -r "from.*domains/check-in'" src/
grep -r "from.*domains/check-in\"" src/
```

If hits are found, repoint them to `'../check-in/utils/divergence.util'` or the appropriate deep path.

### Step 4.4: Delete `providers/` directory

Delete the entire `providers/` directory:

```bash
rm -rf src/app/domains/check-in/providers/
```

**Verification**: Confirm `check-in-initializer` is not referenced anywhere:

```bash
grep -r "check-in-initializer\|provideCheckInInitializer" src/
```

This should return zero hits (already confirmed dead code, removed from `app.config`).

### Step 4.5: Create `pages/index.ts` barrel

Create `src/app/domains/check-in/pages/index.ts` with all page exports:

```typescript
export * from './check-in-start/check-in-start.page';
export * from './check-in-rating/check-in-rating.page';
export * from './check-in-submit/check-in-submit.page';
export * from './check-in-comparison/check-in-comparison.page';
export * from './check-in-trends/check-in-trends.page';
```

This matches the tasks pattern at `src/app/domains/tasks/pages/index.ts`.

### Step 4.6: Remove `standalone: true` from page components

Angular 19 with `"standalone": true` in `angular.json` schematics means all components are standalone by default. The tasks domain does NOT include `standalone: true` in its `@Component` decorators. Remove the explicit flag from:

1. **`check-in-rating.page.ts`** (line 43) — remove `standalone: true,`
2. **`check-in-submit.page.ts`** (line 42) — remove `standalone: true,`
3. **`check-in-comparison.page.ts`** (line 49) — remove `standalone: true,`
4. **`check-in-trends.page.ts`** (line 29) — remove `standalone: true,`

`check-in-start.page.ts` already does NOT have the flag (matches canonical).

### Step 4.7: Replace `CommonModule` with `SharedModule`

The tasks domain uses `SharedModule` (from `@app/shared`), never `CommonModule` directly. Four check-in pages import `CommonModule` instead:

1. **`check-in-rating.page.ts`**: Replace `import { CommonModule } from '@angular/common';` with `import { SharedModule } from '@app/shared';` and change the `imports` array entry from `CommonModule` to `SharedModule`.

2. **`check-in-submit.page.ts`**: Same replacement.

3. **`check-in-comparison.page.ts`**: Same replacement.

4. **`check-in-trends.page.ts`**: Same replacement.

`check-in-start.page.ts` already uses `SharedModule` (matches canonical).

### Step 4.8: Fix service imports to use barrel

The tasks domain imports services from the barrel (`../../services`). Check each check-in page:

- **`check-in-start.page.ts`** (line 14): Uses `'../../services/check-in-start-page/check-in-start-page.service'` -- change to `'../../services'`

- **`check-in-rating.page.ts`** (lines 24-26): Uses direct deep paths for `CheckInExpiryService`, `CheckInRatingPageService`, `CheckInService` -- change all three to a single import from `'../../services'`

- **`check-in-submit.page.ts`** (lines 26-28): Uses direct paths for `CheckInSubmitPageService` and `CheckInRatingPageService` -- change to `'../../services'`

- **`check-in-comparison.page.ts`** (lines 24-25): Uses direct path for `CheckInComparisonPageService` -- change to `'../../services'`

- **`check-in-trends.page.ts`** (line 18): Uses direct path for `CheckInTrendsPageService` -- change to `'../../services'`

The services barrel at `services/index.ts` already exports all these services, so no changes needed there.

### Step 4.9: Verify route guards match pattern

Compare check-in routes with tasks:

| Route type | Tasks pattern | Check-in current | Action |
|------------|--------------|------------------|--------|
| List-like (start) | `canDeactivate: [leavePageGuard]` | `canDeactivate: [leavePageGuard]` | OK |
| Form-like (rating) | `canDeactivate: [canDeactivateGuard, leavePageGuard]` | `canDeactivate: [canDeactivateGuard, leavePageGuard]` | OK |
| Submit | N/A in tasks | No guard | OK (read-only status page) |
| Comparison | N/A in tasks | No guard | OK (read-only result page) |
| Trends | N/A in tasks | No guard | OK (read-only display page) |

No changes needed. The start page has `leavePageGuard` (list-like, matches `TaskListPage`). The rating page has both guards (form-like, matches `TaskUpsertPage`). Submit/comparison/trends are display-only pages with no unsaved state, so no guards are appropriate.

---

## 5. File Inventory

### Files Created (1)
- `src/app/domains/check-in/pages/index.ts`

### Files Renamed (1)
- `src/app/domains/check-in/check-in.routes.ts` -> `src/app/domains/check-in/routes.ts`

### Files Deleted (2)
- `src/app/domains/check-in/index.ts`
- `src/app/domains/check-in/providers/check-in-initializer.ts` (and the `providers/` dir)

### Files Modified (6)
- `src/app/domains/tabs/routes.ts` (update import path)
- `src/app/domains/check-in/pages/check-in-start/check-in-start.page.ts` (barrel import)
- `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts` (remove standalone, CommonModule -> SharedModule, barrel imports)
- `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.ts` (remove standalone, CommonModule -> SharedModule, barrel imports)
- `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.ts` (remove standalone, CommonModule -> SharedModule, barrel imports)
- `src/app/domains/check-in/pages/check-in-trends/check-in-trends.page.ts` (remove standalone, CommonModule -> SharedModule, barrel imports)

---

## 6. Testing

1. **Build check**: `ng build` must pass with zero errors.
2. **Lint check**: `npx eslint src/app/domains/check-in/` must pass.
3. **Unit tests**: `npx jest --testPathPattern="check-in"` (if any exist).
4. **Manual smoke test**:
   - Navigate to check-in tab -> start page loads.
   - Select partner -> rating page loads.
   - Complete ratings -> submit page loads.
   - Submit -> comparison page loads.
   - Navigate to trends -> trends page loads.
5. **Import verification**: `grep -r "check-in.routes\|check-in-initializer\|CommonModule" src/app/domains/check-in/` returns zero hits after changes.

---

## 7. Rollback

All changes are purely structural (renames, deletes, import path changes). If build breaks:

1. Revert the rename: `git mv routes.ts check-in.routes.ts`
2. Restore `tabs/routes.ts` import path
3. Restore `index.ts` and `providers/` from git

---

## 8. Architecture Notes

### Final check-in domain layout (after this task)

```
src/app/domains/check-in/
├── routes.ts                    # Route definitions (renamed)
├── components/                  # Domain-specific widgets
│   ├── divergence-alert/
│   ├── quality-bar/
│   ├── question-card/
│   ├── question-drilldown/
│   ├── sparkline/
│   ├── tap-circle-rating/
│   └── trend-toggle/
├── constants/                   # Questions + expiry config
│   ├── expiry.ts
│   └── questions.ts
├── interfaces/                  # Domain types
├── pages/                       # Page components
│   ├── index.ts                 # Barrel (new)
│   ├── check-in-start/
│   ├── check-in-rating/
│   ├── check-in-submit/
│   ├── check-in-comparison/
│   └── check-in-trends/
├── services/                    # Page services + data services
│   ├── index.ts                 # Barrel (existing)
│   ├── check-in/
│   ├── check-in-comparison-page/
│   ├── check-in-expiry/
│   ├── check-in-local-storage/
│   ├── check-in-rating-page/
│   ├── check-in-sqlite/
│   ├── check-in-start-page/
│   ├── check-in-submit-page/
│   └── check-in-trends-page/
└── utils/                       # Pure computation functions
    ├── date.util.ts
    ├── date.util.spec.ts
    ├── divergence.util.ts
    ├── divergence.util.spec.ts
    ├── quality.util.ts
    └── quality.util.spec.ts
```

### Comparison with tasks

```
src/app/domains/tasks/
├── routes.ts
├── interfaces/
├── pages/
│   ├── index.ts
│   ├── task-list/
│   └── task-upsert/
└── services/
    ├── index.ts
    ├── task-list-page/
    ├── task-upsert-page/
    ├── tasks/
    ├── tasks-local-storage/
    └── tasks-sqlite/
```

---

## 9. Justified Deviations

These structural differences from tasks are intentional and should NOT be removed:

| Extra in check-in | Justification |
|-------------------|---------------|
| `constants/` folder | Contains 10 check-in questions and expiry timeout config. These are static domain data, not service logic. Inlining 40+ lines of question definitions into a service would violate SRP. Tasks has no equivalent static config. |
| `utils/` folder | Houses pure computation functions (quality scoring, divergence detection, date normalization). These are stateless, testable functions that don't need DI. Tasks uses only CRUD operations with no domain math. |
| `components/` folder | Domain-specific presentation widgets (tap-circle ratings, sparkline charts, quality bars, trend toggles, divergence alerts, question drilldowns). Tasks' simple text list/form UI needs no custom widgets. |
| 5 pages vs 2 | Check-in is a multi-step flow (start -> rate -> submit -> wait-for-partner -> compare -> trends). Tasks is a simple list + upsert CRUD. The page count reflects domain complexity, not structural drift. |
| `CheckInExpiryService` | Manages 48-hour session lifecycle (expire stale, cleanup expired). Tasks are permanent records with no time-based lifecycle. This service is domain-essential, not cruft. |

---

## 10. Commit Strategy

Single commit covering all changes:

```
refactor(check-in): align domain structure with tasks CRUD pattern

- Rename check-in.routes.ts -> routes.ts
- Delete dead providers/check-in-initializer.ts
- Delete root index.ts barrel (tasks doesn't have one)
- Add pages/index.ts barrel export
- Replace CommonModule with SharedModule in 4 pages
- Remove redundant standalone: true (Angular 19 default)
- Repoint service imports to barrel
- Update tabs/routes.ts loadChildren path
```

---

## 11. Edge Cases

1. **Circular imports**: The pages barrel (`pages/index.ts`) only exports page classes. Pages import from `../../services` (the services barrel). Services never import from pages. No circular risk.

2. **Lazy loading**: Routes use `loadComponent: () => import('./pages/...')` with direct file paths, NOT the barrel. The barrel is for external consumers (like tests or other domains if needed). Do not change the route `import()` paths to use the barrel -- tree-shaking requires direct paths in lazy routes.

3. **SharedModule vs CommonModule**: `SharedModule` re-exports `CommonModule` plus app-wide directives/pipes. Switching from `CommonModule` to `SharedModule` only adds capabilities, never removes them. No template breakage possible.

4. **`standalone: true` removal**: Angular 19 with `angular.json` schematic default `"standalone": true` means the CLI generates standalone components. However, the runtime behavior is controlled by the decorator, not the schematic. In Angular 19, components without `standalone: true` in the decorator are still module-based by default. **Check**: If `tsconfig.json` or `angular.json` has no runtime standalone default, you may need to KEEP `standalone: true`. Verify by removing it from one file, running `ng build`, and checking for errors. If build fails, revert and keep the flag.

   **Update (Angular 19.1+)**: Starting Angular 19, `standalone: true` is the default for `@Component`. The flag is redundant and can be safely removed. The tasks domain already omits it, confirming this project uses the default.

---

## 12. Definition of Done

- [ ] `ng build` passes with zero errors
- [ ] `npx eslint src/app/domains/check-in/ --max-warnings=0` passes
- [ ] No references to `check-in.routes` remain in codebase
- [ ] No references to `check-in-initializer` remain in codebase
- [ ] No `CommonModule` imports in any check-in page
- [ ] No explicit `standalone: true` in any check-in page
- [ ] All page service imports use the barrel (`../../services`)
- [ ] `pages/index.ts` barrel exists and exports all 5 pages
- [ ] `providers/` directory no longer exists
- [ ] Domain root has no `index.ts`
- [ ] Tab navigation to check-in still works (manual test)
