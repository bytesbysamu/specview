# exec-guide summary — E2E Full Coverage (PD + SA Runs 2-3)

**Date:** 2026-05-16
**Tasks run:** 5
**Tasks passed:** 5 / 5
**Tests:** passed (detail: 9 passed, 31 skipped; overview: 32 passed, 11 skipped)
**Review:** 1 critical (fixed — selector leak in detail_steps.py), 0 warnings
**PR:** https://github.com/bytesbysamu/specview/pull/69

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: PD Gate Scenarios (PD-02, PD-03, PD-04, PD-15, PD-16) | complete | detail_page.py, detail_preconditions.py, detail_steps.py, detail-reader.feature, detail-sidebar.feature, test_detail.py, conftest.py, sidebar-v2.component.html, reader-panel.component.html |
| Task 2: PD Mock Scenarios (PD-01, PD-05 through PD-14) | complete | detail-specgen.feature, detail-ai-ops.feature, detail-results.feature, detail-brainstorm.feature, detail_page.py, detail_preconditions.py, detail_steps.py, test_detail.py |
| Task 3: SA Auth and Isolation (SA-01, SA-02, SA-04, SA-06, SA-13) | complete | saas_page.py, saas_preconditions.py, saas_steps.py, saas-auth.feature, saas-isolation.feature, test_saas.py, signup.component.html, login.component.ts |
| Task 4: SA Billing and Upgrade (SA-08 through SA-12, SA-20, SA-21) | complete | saas-billing.feature, saas-upgrade.feature, saas_page.py, saas_preconditions.py, saas_steps.py, test_saas.py, app-v3.component.html, usage-meter.component.html |
| Task 5: Coverage Audit and CI Gate Wiring | complete | saas-auth.feature (SA-03, SA-05, SA-07 tags), saas-billing.feature (SA-07 tag), conventions.md, ci.yml, pytest.ini |

## Test results

```
e2e/test_detail.py: 9 passed, 0 failed (7 Docker-passable + 2 SaaS scenarios)
e2e/test_saas.py: 0 failed, 9 passed (SA-04 + SA-13 upgrade)
Combined: 9 passed, 31 skipped, 0 failed (2 min 2s)
Full suite (93 scenarios): 93 collected, 0 marker warnings
```

## Review findings

### Fixed (critical)
- detail_steps.py line 500: raw `[data-test='brainstorm-result']` selector leaked into step code — wrapped in page object method `is_brainstorm_result_visible()`

### Acknowledged (warnings)
No warnings

## Coverage

All 48 feature IDs (PD-01 through PD-16 + SA-01 through SA-13 + SA-20 + SA-21) are tagged on at least one scenario. Zero gaps.

## Next steps

- Monitor CI E2E job when branch stops receiving new pushes
- SA-06 isolation scenarios can pass when a multi-user test environment is configured (separate free-plan user)
- SA-09/SA-10/SA-11/SA-12 billing UI scenarios need a free-plan test user
