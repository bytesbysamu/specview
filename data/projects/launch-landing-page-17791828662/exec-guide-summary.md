# exec-guide summary — Launch: Landing Page with CTA Funnel

**Date:** 2026-05-19
**Tasks run:** 4
**Tasks passed:** 4 / 4
**Tests:** passed (backend: modules/ai — 276 passed, frontend: 489/490 passed)
**Review:** 3 critical (all fixed), 6 warnings
**PR:** https://github.com/bytesbysamu/specview/pull/91 (merged)
**Follow-up PR:** https://github.com/bytesbysamu/specview/pull/92 (demo-data rename fix)

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Design Token Extraction | ✓ complete | landing/tokens.css, landing/index.html |
| Task 2: Landing-to-App Data Transfer Contract | ✓ complete | landing/redirect.js, web-ng/src/app/landing-handoff.service.ts, web-ng/src/app/app.routes.ts |
| Task 3: Landing Page Braindump UI | ✓ complete | landing/index.html, landing/demo-content.js, landing/rotation.js, landing/redirect.js |
| Task 4: App Demo & Real Mode Integration | ✓ complete | web-ng/src/app/demo-result/*, web-ng/src/app/analyze-result/*, web-ng/public/demo-data/*.json, api/modules/ai/routes/text.py, api/openapi.yaml |

## Test results

- Backend: 276 passed (modules/ai), then 14 passed after scoping
- Frontend: 490 tests, 489 passed, 1 fakeAsync test fixed during CI
- E2E: 7 pre-existing failures (same on master since PR #89), not introduced by this PR

## Review findings

### Fixed (critical)
1. Anonymous bootstrap status endpoint delegated to auth-protected function — extracted `_bootstrap_status_impl`
2. Missing demo-result component spec file — created with 6 tests
3. Missing analyze-result component spec file with fakeAsync polling tests — created with 5 tests

### Acknowledged (warnings)
1. Unused `ActivatedRoute` import in DemoResultComponent — fixed
2. Unused `date_type` import in text.py — fixed
3. `_ANON_IP_COUNTS` dict has no eviction strategy — acknowledged
4. `APP_ORIGIN` hardcoded fallback breaks local dev — fixed (localhost detection)
5. Double-wrapped OR fallback in redirect.js — acknowledged
6. Mock factory missing service methods — fixed

## Post-merge fixes (PR #92)
- Renamed `public/demo/` → `public/demo-data/` to avoid nginx 403 on `/demo` route
- Production nginx was treating `/demo` as a directory listing instead of SPA fallback

## Next steps
- Merge PR #92 (demo-data rename)
- Deploy to VPS and verify specview.dev → app.specview.dev/demo flow end-to-end
- Manual: verify typewriter animation on landing page
- Manual: verify demo mode instant result + real mode API polling
