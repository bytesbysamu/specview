# E2E Full Coverage — PD + SA (Runs 2-3)

## Context

54 features across 3 domains. Run 1 (Overview, OV-01–OV-13) is complete with 43 E2E scenarios (32 pass, 11 skip). This braindump covers the remaining two runs to achieve full E2E coverage.

Feature specs source: `test-phase1-feature-specs-1778592995/feature-specs.md` (3,280 lines on VPS). The original file uses OV-14–OV-33 for detail features — we renamed these to PD-01–PD-16 during this session. SA features are SA-01–SA-21.

## Run 1 recap (DONE)

- 17 features: OV-01 (auth gate) through OV-13 (create modal) + OV-14–17 (pure functions, unit tested)
- 43 Gherkin scenarios across 9 `overview-*.feature` files
- 32 pass, 11 skip (mock-dependent)
- Page object: `e2e/pages/overview_page.py`
- Steps: `e2e/steps/overview_preconditions.py` + `overview_steps.py`

---

## Run 2: Project Detail (PD-01 to PD-16)

### Features to cover

From feature-specs.md (VPS), originally OV-14 to OV-27 + OV-32–OV-33, renamed to PD:

| ID | Feature | E2E-testable? |
|----|---------|---------------|
| PD-01 | Spec-gen pipeline with incremental file save | Yes (needs mock) |
| PD-02 | Expanded project reader panel | Yes |
| PD-03 | Reader sidebar | Yes |
| PD-04 | Sidebar status row | Yes |
| PD-05 | Per-file dot tracking | Yes (needs mock) |
| PD-06 | Generate Specs button | Yes (needs mock) |
| PD-07 | Generate Guide button | Yes (needs mock) |
| PD-08 | AI text ops chips | Partial (toggle visible, ops need mock) |
| PD-09 | Style preset chips | Partial |
| PD-10 | AI result panel with diff view | Needs mock |
| PD-11 | Result toolbar (Apply/Copy/Dismiss) | Needs mock |
| PD-12 | Undo/redo stack | Needs mock (requires apply first) |
| PD-13 | Brainstorm follow-up input | Needs mock |
| PD-14 | Generate Specs from brainstorm | Needs mock |
| PD-15 | Spec file canonical ordering | Yes (check sidebar order) |
| PD-16 | Markdown rendering with XSS sanitization | Yes |

### Proposed feature files (~35 scenarios)

| File | Features | Scenarios |
|------|----------|-----------|
| `detail-reader.feature` | PD-02, PD-15, PD-16 | 5: panel opens, markdown renders, file ordering, XSS stripped |
| `detail-sidebar.feature` | PD-03, PD-04, PD-05 | 5: file nav, status row states, dot tracking |
| `detail-specgen.feature` | PD-01, PD-06, PD-07 | 6: pipeline start/poll/complete, generate buttons, guide button |
| `detail-ai-ops.feature` | PD-08, PD-09 | 5: chip toggle, style presets visible, only-when-spec-open |
| `detail-results.feature` | PD-10, PD-11, PD-12 | 5: diff view, toolbar actions, undo/redo |
| `detail-brainstorm.feature` | PD-13, PD-14 | 4: follow-up input, generate from brainstorm |

### New infrastructure needed
- `e2e/pages/detail_page.py` — extends OverviewPage with expanded panel selectors
- `e2e/steps/detail_preconditions.py` — Given steps for "a project is open with spec files"
- `e2e/steps/detail_steps.py` — When/Then for sidebar clicks, reader content, AI ops
- Seed data: 1 project with braindump + full spec set (analysis, epic, architecture, impl guide)

### What can run against Docker (no mock)
- PD-02: panel opens when project clicked
- PD-03: sidebar shows file list
- PD-04: status row displays "connected"
- PD-15: files in canonical order (braindump → analysis → epic → architecture → timeline → impl-guide)
- PD-16: markdown renders, script tags stripped

### What needs mock (skip against Docker)
- PD-01, PD-05, PD-06, PD-07: spec generation pipeline
- PD-08–PD-14: AI text operations, results, undo/redo, brainstorm

---

## Run 3: SaaS (SA-01 to SA-21)

### Features to cover

| ID | Feature | E2E-testable? |
|----|---------|---------------|
| SA-01 | Login page | Yes |
| SA-02 | Signup / registration page | Yes |
| SA-03 | Auth service | Implicit (via login/signup tests) |
| SA-04 | Token lifecycle service | Yes (expiry → redirect) |
| SA-05 | Auth HTTP interceptor | Implicit |
| SA-06 | Project ownership 403 handling | Yes (multi-user) |
| SA-07 | Subscription service | Implicit (via billing tests) |
| SA-08 | Billing HTTP interceptor | Yes (429 → upgrade redirect) |
| SA-09 | Usage remaining shared state | Yes (header check) |
| SA-10 | Usage meter component | Yes (visible for free, hidden for pro) |
| SA-11 | Upgrade button in masthead | Yes |
| SA-12 | Upgrade page | Yes |
| SA-13 | Full-page route routing bypass | Yes (/signup, /upgrade render without app shell) |
| SA-14 | IP-based rate limiting | Backend only — pytest |
| SA-15 | Security headers | Backend only — pytest |
| SA-16 | Security canary endpoint | Backend only — pytest |
| SA-17 | SKIP_AUTH environment gating | Backend only — pytest |
| SA-18 | Project isolation enforcement | Backend only — pytest |
| SA-19 | Billing 429 usage header | Backend only — pytest |
| SA-20 | Lapsed plan state | Yes (UI shows different CTA) |
| SA-21 | Stripe checkout and session verify | Partial (redirect testable, actual Stripe needs mock) |

### Proposed feature files (~25 scenarios)

| File | Features | Scenarios |
|------|----------|-----------|
| `saas-auth.feature` | SA-01, SA-02, SA-04, SA-13 | 6: login, signup, token expiry redirect, full-page routes |
| `saas-isolation.feature` | SA-06 | 4: user A can't see user B's project, 403 UI, back button |
| `saas-billing.feature` | SA-08, SA-09, SA-10, SA-11 | 5: 429 redirect, usage meter, upgrade button, remaining count |
| `saas-upgrade.feature` | SA-12, SA-20, SA-21 | 5: upgrade page states (free/lapsed/pro), checkout redirect, manage subscription |

### New infrastructure needed
- `e2e/pages/saas_page.py` — login form, signup form, upgrade page selectors
- `e2e/steps/saas_preconditions.py` — multi-user setup (user A + user B), plan state injection
- `e2e/steps/saas_steps.py` — auth flow assertions, billing UI checks
- Multi-user auth: create user B via API, generate separate JWTs
- Plan state: need ability to set user's plan to free/pro/lapsed for testing

### What can run against Docker
- SA-01, SA-02: login/signup forms render and submit
- SA-04: expired JWT → redirect to login
- SA-06: user B gets 403 on user A's project (needs two real users in DB)
- SA-10: usage meter visible for free user
- SA-11: upgrade button visible for non-pro
- SA-12: upgrade page renders with correct state
- SA-13: /signup and /upgrade render via router-outlet

### What needs mock or Stripe test mode
- SA-08: 429 response (need to hit rate limit or mock it)
- SA-20: lapsed state (need Stripe webhook simulation)
- SA-21: checkout redirect (real Stripe test mode or mock)

---

## Shared pipeline (same as Run 1)

The parameterized E2E pipeline from Test Phase 2 applies to all runs:
1. Derive scenarios from feature spec State Matrix
2. Identify new step definitions needed
3. Extend page objects with selectors
4. Implement step definitions
5. Seed test data
6. Run and verify

### Reuse from Run 1
- `e2e/conftest.py` — session fixtures, JWT injection, E2E_BASE_URL support
- `e2e/steps/overview_preconditions.py` — login/logout steps reusable by all runs
- `e2e/pages/overview_page.py` — base selectors reusable
- `e2e/helpers/seed_projects.py` — project seeding via API
- `e2e/docs/conventions.md` — tagging, step style, naming conventions

### New for Runs 2-3
- `e2e/test_detail.py` — scenarios() registration for PD feature files
- `e2e/test_saas.py` — scenarios() registration for SA feature files

## Target

| Run | Features | Scenarios | Pass (Docker) | Skip (mock) |
|-----|----------|-----------|---------------|-------------|
| 1 (OV) | 17 | 43 | 32 | 11 |
| 2 (PD) | 16 | ~35 | ~15 | ~20 |
| 3 (SA) | 21 | ~25 | ~15 | ~10 |
| **Total** | **54** | **~103** | **~62** | **~41** |

## Success criteria
- Every feature from OV-01 to SA-21 has at least one E2E scenario tagged with its ID
- All scenarios pass against Docker or correctly skip with _SKIP_MOCK
- Page objects for all 3 domains (overview, detail, saas) follow the same pattern
- `ng build` passes, no Karma regressions
- Conventions from e2e/docs/conventions.md followed (tags, step style, naming)
