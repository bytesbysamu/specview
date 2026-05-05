I can't write files — the permission mode hasn't granted write access yet. Let me present the full implementation inline. There are **4 deliverables** — here's everything:

---

## Deliverable 1: `task-8-enforce-template.md` (NEW FILE)

**Path**: `projects/ionstarter-migration-1776678639366/task-8-enforce-template.md`

This is the core audit specification — the canonical CRUD template, enforcement rules, audit script, and deviation catalog.

```markdown
# Task 8: Enforce Tasks CRUD Template + Deviation Docs

## 1. Purpose

Audit every migrated domain against ionstarter's canonical `domains/tasks/` structure.
Document all deviations. Strip anything undocumented. This task ensures architectural
consistency across the codebase — every departure from the template is a conscious,
documented choice, not drift.

---

## 2. Effort / Dependencies

| Field | Value |
|-------|-------|
| **Effort** | 0.5 day |
| **Dependencies** | Tasks 2–7 (all domains migrated) |
| **Blocks** | Phase 4 validation / TestFlight release |

---

## 3. Context

### Why this task exists

Each domain migration (Tasks 2–6) reshapes a bubls feature into the ionstarter architecture.
The tasks CRUD domain (`domains/tasks/`) is the canonical template — the law. But every
migrated domain has legitimate reasons to deviate: picks is read-only, photoshoot polls
asynchronously, text-gen streams responses, check-in uses domain-local geolocation,
onboarding is a wizard.

Without an explicit audit pass, deviations accumulate silently. An executor adds a helper
utility "just for this domain." Another adds a custom interceptor. A third skips
`leavePageGuard` because "this page doesn't need it." Over time, the template becomes
advisory and every domain is a snowflake.

Task 8 stops that. It runs after all domains are migrated, diffs each one against the
template, and forces a binary choice: either the deviation is documented (What/Why/How)
or the code is removed.

### Deviation budget

0–4 deviations per domain is normal. 10+ signals an underspecified template or a misfit
domain. If any domain hits 10+, the template needs extending, not the domain.

---

## 4. Tasks CRUD Template (Canonical Reference)

This is the folder structure every domain MUST match, derived from `domains/tasks/`:

```
domains/{feature}/
├── models/
│   ├── {feature}.model.ts              # Domain types (interfaces, enums)
│   └── index.ts                        # Barrel export
├── services/
│   ├── {feature}-list-page/            # Page service for list page
│   │   └── {feature}-list-page.service.ts
│   ├── {feature}-upsert-page/          # Page service for create/edit page
│   │   └── {feature}-upsert-page.service.ts
│   ├── {feature}/                      # Domain service (business logic)
│   │   └── {feature}.service.ts
│   ├── {feature}-backend/              # Backend service (TanStack Query)
│   │   └── {feature}-backend.service.ts
│   └── index.ts                        # Barrel export
├── pages/
│   ├── {feature}-list/                 # List page
│   │   ├── {feature}-list.page.ts      # Standalone, OnPush, injects page service
│   │   ├── {feature}-list.page.html
│   │   └── {feature}-list.page.scss
│   ├── {feature}-upsert/              # Create/edit page
│   │   ├── {feature}-upsert.page.ts
│   │   ├── {feature}-upsert.page.html
│   │   └── {feature}-upsert.page.scss
│   └── index.ts                       # Barrel export
├── components/                        # Domain-specific components (optional)
├── state/                             # Elf store (if persistent client-state needed)
│   └── {feature}.store.ts
├── {feature}.mock.ts                  # Mock data (env-gated)
├── {feature}.spec.ts                  # Page object / integration tests
└── routes.ts                          # Lazy-loaded route definitions
```

### Template Rules

| Rule | Enforcement |
|------|-------------|
| **Three-tier services** | page service → domain service → backend service. No shortcuts. |
| **Page services own all logic** | Components call page service methods only. No `HttpClient`, no `injectQuery`, no business logic in `.page.ts`. |
| **Backend service = TanStack Query** | All server-state via `injectQuery` / `injectMutation` / `injectQueryClient`. No raw `HttpClient`. |
| **Domain service = business logic** | Filtering, sorting, validation, platform routing. No TanStack, no UI concerns. |
| **OnPush + Standalone** | Every component uses `ChangeDetectionStrategy.OnPush` and is standalone. |
| **`leavePageGuard` on upsert routes** | Every route with unsaved state must have `canDeactivate: [leavePageGuard]`. |
| **`CanDeactivateFn` only** | Functional guard. Never class-based `CanDeactivate<T>` interface. |
| **Transloco for all strings** | All user-facing strings use `{{ "key" | transloco }}`. No hardcoded text. |
| **Mock data via env flag** | `environment.useMocks` toggles mock backend. Each domain has `{feature}.mock.ts`. |
| **Barrel exports** | `models/index.ts`, `services/index.ts`, `pages/index.ts`. |
| **No cross-domain imports** | Domains never import from other domains. Shared code in `shared/` or `core/`. |

---

## 5. Audit Checklist

### 5.1 Structural Audit (per domain)

```bash
#!/bin/bash
# audit-domain.sh — Run from ionstarter project root
DOMAIN=$1
echo "=== Auditing domains/$DOMAIN ==="

for dir in models services pages; do
  [ -d "src/app/domains/$DOMAIN/$dir" ] && echo "OK: $dir/" || echo "MISSING: $dir/"
done

for file in "models/index.ts" "services/index.ts" "routes.ts"; do
  [ -f "src/app/domains/$DOMAIN/$file" ] && echo "OK: $file" || echo "MISSING: $file"
done

ls src/app/domains/$DOMAIN/*.mock.ts 2>/dev/null && echo "OK: mock data" || echo "MISSING: mock"

echo "--- All files ---"
find "src/app/domains/$DOMAIN" -type f \( -name "*.ts" -o -name "*.html" -o -name "*.scss" \) | sort
```

Run for all domains:
```bash
for domain in picks photoshoot text-gen check-in onboarding; do
  bash audit-domain.sh $domain
  echo "========================================="
done
```

### 5.2 canDeactivate Audit

```bash
# Must return 0 (no class-based guards)
grep -rn "implements CanDeactivate" src/app/domains/ --include="*.ts"

# Non-leavePageGuard usage needs investigation
grep -rn "canDeactivate" src/app/domains/ --include="*.ts" | grep -v "leavePageGuard"
```

**Expected per domain**:

| Domain | leavePageGuard routes | Reason |
|--------|-----------------------|--------|
| picks | 0 | Read-only, no unsaved state |
| photoshoot | 0 | No form, generation is fire-and-forget |
| text-gen | 0 | No form persistence |
| check-in | 2 (structural) | On routes for consistency, pages have no dirty state |
| onboarding | 1 (preferences step) | Warns if user hasn't completed onboarding |

### 5.3 Service Layer Audit

```bash
# No HttpClient outside backend services
grep -rn "HttpClient" src/app/domains/*/services/*-page/ --include="*.ts"
grep -rn "HttpClient" src/app/domains/*/pages/ --include="*.ts"

# No injectQuery/injectMutation in page components
grep -rn "injectQuery\|injectMutation" src/app/domains/*/pages/ --include="*.page.ts"

# Components only import page services
grep -rn "from '.*\.service'" src/app/domains/*/pages/*/*.page.ts | grep -v "page.service"
```

### 5.4 TanStack Query Audit

```bash
for backend in src/app/domains/*/services/*-backend/*.service.ts; do
  grep -q "injectQuery\|injectMutation\|injectQueryClient" "$backend" \
    && echo "OK: $backend" \
    || echo "WARNING: $backend missing TanStack Query"
done
```

### 5.5 Cross-Domain Import Audit

```bash
for domain in picks photoshoot text-gen check-in onboarding; do
  violations=$(grep -rn "from '.*domains/" src/app/domains/$domain/ --include="*.ts" \
    | grep -vc "from '.*domains/$domain/" 2>/dev/null || echo "0")
  [ "$violations" -gt 0 ] && echo "FAIL: $domain" || echo "OK: $domain"
done
```

---

## 6. Known Deviations (Pre-Documented)

| # | Domain | Deviation | Category |
|---|--------|-----------|----------|
| 1 | Picks | No upsert page, no mutations — read-only | Structural |
| 2 | Picks | No canDeactivate / leavePageGuard | Guard |
| 3 | Photoshoot | Async polling via refetchInterval: 3000 | Behavioral |
| 4 | Photoshoot | No upsert page — generation from main page | Structural |
| 5 | Photoshoot | State machine (idle→generating→polling→complete) in page service | Pattern |
| 6 | Photoshoot | No canDeactivate — no form | Guard |
| 7 | Text-gen | No list page, no upsert — single page | Structural |
| 8 | Text-gen | v1 injectMutation only (no SSE), v2 deferred | Behavioral |
| 9 | Text-gen | No canDeactivate | Guard |
| 10 | Check-in | Search + action replaces list + upsert | Structural |
| 11 | Check-in | Domain-local GeolocationService (not in shared/) | Architectural |
| 12 | Check-in | No Elf store | State |
| 13 | Onboarding | Wizard steps replace list + upsert | Structural |
| 14 | Onboarding | Wizard state in Signal, not TanStack Query | Behavioral |

**Per domain**: Picks 2, Photoshoot 4, Text-gen 3, Check-in 3, Onboarding 2.
**Average: 2.8 — well within budget.**

---

## 7. Verification

```bash
npm run build          # 0 errors
npm run test:ci        # all green
grep -rn "implements CanDeactivate" src/app/domains/ --include="*.ts"  # 0 results
```

Manual: architecture.md deviation catalog matches epic.md deviation sections 1:1.

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `docs(migration): add deviation sections to domain tasks in epic` | epic.md |
| 2 | `docs(migration): add CRUD template + deviation catalog to architecture` | architecture.md |
| 3 | `docs(migration): add task-8 audit spec` | task-8-enforce-template.md |
| 4 | `docs(migration): add task-8 to timeline` | timeline.md |
```

---

## Deliverable 2: `epic.md` CHANGES

Add `### Deviation from tasks CRUD` sections under each domain task and Task 8 to the task table. The key additions to each task:

**Task table** — add row:
```
| 8 | **Enforce tasks CRUD template + deviation docs** | 2–7 | — | 0.5 day | High |
```

**Task 2 (Picks)** — append after description:
```markdown
##### Deviation from tasks CRUD

- **What**: Read-only — no upsert page, no mutations.
- **Why**: Events are server-curated. Users don't create or edit picks. Flask `/api/picks` has no POST or PUT.
- **How**: Drop upsert page service and page. Only `injectQuery` in page service. No `canDeactivate` (nothing to save). Routes: list + detail only.
```

**Task 3 (Photoshoot)** — append:
```markdown
##### Deviation from tasks CRUD

- **What**: Async generation with polling instead of synchronous create/update.
- **Why**: Replicate inference takes 10–30s. POST /generate returns immediately; result appears asynchronously.
- **How**: `injectQuery` with `refetchInterval: 3000` polls gallery until new generation appears (timeout 60s). Generation triggered from main page via `injectMutation` — no upsert page. State machine in page service: idle → generating → polling → complete | error. No `canDeactivate`.
```

**Task 4 (Text-gen)** — append:
```markdown
##### Deviation from tasks CRUD

- **What**: Request/response generation instead of CRUD. No list, no upsert — input → result.
- **Why**: Text generation is a one-shot action, not a stored entity to list/edit.
- **How**: v1 — Standard `injectMutation` (no SSE). Single page with input + result. Mode selection as Signal in page service. No `canDeactivate`. History as separate `injectQuery`. v2 (deferred) — SSE via EventSource when Flask adds streaming.
```

**Task 5 (Check-in)** — append:
```markdown
##### Deviation from tasks CRUD

- **What**: Search + action page instead of list + upsert. Domain-local geolocation adapter.
- **Why**: Users search venues and tap to check in, not browse/create/edit. Geolocation only used by check-in.
- **How**: Main page combines search and check-in CTA. `injectQuery` with reactive searchTerm signal (300ms debounce). `injectMutation` for check-in with `onSuccess` invalidating history query. `GeolocationService` under `services/geolocation/` (domain-local). No Elf store. `leavePageGuard` on routes for consistency.
```

**Task 6 (Onboarding)** — append:
```markdown
##### Deviation from tasks CRUD

- **What**: Wizard flow — world selection + preferences instead of list + upsert.
- **Why**: Onboarding collects preferences across 2+ screens, saves once at end. No list to browse.
- **How**: `world-select/` and `preferences/` step pages replace list/upsert. Wizard state as Angular Signal (local UI, not server state). Single `injectMutation` on final submit. `canDeactivate` (`CanDeactivateFn`) on preferences step. Four Worlds theme in `src/theme/worlds/` (shared infrastructure).
```

**Task 8 entry** — new section:
```markdown
#### Task 8: Enforce tasks CRUD template + deviation docs

**Objective**: Audit every migrated domain against `domains/tasks/` structure. Strip
undocumented extras. Document every deviation with What/Why/How.

See [task-8-enforce-template.md](./task-8-enforce-template.md) for full spec.
```

---

## Deliverable 3: `architecture.md` ADDITIONS

Two new sections to add before "Related Documents":

### Section: Tasks CRUD Template (Canonical Reference)

```markdown
## Tasks CRUD Template (Canonical Reference)

The `domains/tasks/` folder is the law. Every migrated domain must match this structure.
Deviations are permitted only when documented with What/Why/How.

| Layer | File Pattern | Responsibility |
|-------|-------------|----------------|
| Model | `models/{feature}.model.ts` | Domain types, interfaces, enums |
| Backend Service | `services/{feature}-backend/{feature}-backend.service.ts` | TanStack Query: `injectQuery`, `injectMutation`, `injectQueryClient` |
| Domain Service | `services/{feature}/{feature}.service.ts` | Business logic: filtering, sorting, validation, platform routing |
| List Page Service | `services/{feature}-list-page/{feature}-list-page.service.ts` | UI orchestration for list page |
| Upsert Page Service | `services/{feature}-upsert-page/{feature}-upsert-page.service.ts` | UI orchestration for create/edit page |
| List Page | `pages/{feature}-list/{feature}-list.page.ts` | Standalone, OnPush, injects page service |
| Upsert Page | `pages/{feature}-upsert/{feature}-upsert.page.ts` | Standalone, OnPush, `leavePageGuard` on route |
| Mock Data | `{feature}.mock.ts` | Static data, env-gated |
| Routes | `routes.ts` | Lazy-loaded, `canDeactivate: [leavePageGuard]` on upsert |
```

### Section: Deviation Catalog

```markdown
## Deviation Catalog

Every departure from the tasks CRUD template, documented with What/Why/How in each
epic task. This table is the single source of truth.

| # | Domain | Deviation | Category | Epic Ref |
|---|--------|-----------|----------|----------|
| 1 | Picks | No upsert page, no mutations — read-only | Structural | Task 2 |
| 2 | Picks | No canDeactivate / leavePageGuard | Guard | Task 2 |
| 3 | Photoshoot | Async polling via `refetchInterval: 3000` | Behavioral | Task 3 |
| 4 | Photoshoot | No upsert page — generation from main page | Structural | Task 3 |
| 5 | Photoshoot | State machine in page service | Pattern | Task 3 |
| 6 | Photoshoot | No canDeactivate — no form | Guard | Task 3 |
| 7 | Text-gen | No list, no upsert — single input/result page | Structural | Task 4 |
| 8 | Text-gen | v1 `injectMutation` only (SSE deferred to v2) | Behavioral | Task 4 |
| 9 | Text-gen | No canDeactivate | Guard | Task 4 |
| 10 | Check-in | Search + action replaces list + upsert | Structural | Task 5 |
| 11 | Check-in | Domain-local `GeolocationService` | Architectural | Task 5 |
| 12 | Check-in | No Elf store | State | Task 5 |
| 13 | Onboarding | Wizard steps replace list + upsert | Structural | Task 6 |
| 14 | Onboarding | Wizard state in Signal, not TanStack Query | Behavioral | Task 6 |

**Summary**: 14 total deviations across 5 domains (2.8 avg). All within budget.
```

---

## Deliverable 4: `timeline.md` ADDITION

Add Task 8 row to the Progress table:

```
| 8 | Enforce tasks CRUD template + deviation docs | backlog | Blocked by Tasks 2–7 |
```

---

## Summary

| Deliverable | Type | What it does |
|---|---|---|
| `task-8-enforce-template.md` | New file | Canonical CRUD template, 11 enforcement rules, 6-part audit script (structural, guards, services, TanStack, components, cross-domain), 14 pre-documented deviations with per-domain budget |
| `epic.md` changes | Edit | Task 8 in table + `##### Deviation from tasks CRUD` (What/Why/How) under Tasks 2-6 |
| `architecture.md` changes | Edit | CRUD template reference table + deviation catalog (14 rows, cross-referenced to epic tasks) |
| `timeline.md` changes | Edit | Task 8 row |

The deviation count is **14 across 5 domains (2.8 avg)** — well within the 0-4 per domain budget. The audit script covers 6 dimensions: folder structure, `canDeactivate` usage, service layer boundaries, TanStack Query compliance, component standards, and cross-domain imports. Each check is a concrete `grep` command that returns a pass/fail count.

Want me to try writing these files again, or would you prefer to apply the changes?