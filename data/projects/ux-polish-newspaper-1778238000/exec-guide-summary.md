# exec-guide summary — UX Polish Newspaper Phase 2

**Date:** 2026-05-09
**Tasks run:** 6 (Tasks 1+2 pre-applied, Tasks 3–6 executed today)
**Tasks passed:** 6 / 6
**Tests:** passed (frontend: web-ng — 5 passed)
**Review:** 4 critical, 6 warnings

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Token & Overline Foundation | ✓ complete (pre-applied) | web-ng/src/styles.css |
| Task 2: Masthead & Nameplate Typography | ✓ complete (pre-applied) | web-ng/src/styles.css, app.component.html |
| Task 3: Overline Adoption Across App | ✓ complete | app.component.ts, app.component.html, styles.css |
| Task 4: Remove Lucide CDN | ✓ complete | web-ng/src/index.html, app.component.ts, app.component.html, styles.css |
| Task 5: Dark-Mode Contrast Fixes | ✓ complete | web-ng/src/styles.css |
| Task 6: Spec File Sidebar Ordering | ✓ complete | web-ng/src/app/services/projects.service.ts |

## Test results

frontend: web-ng — 5 passed, 0 failed

## Review findings

**Critical (must fix before merge):**
1. `app.component.ts:241,263,270` — XSS: `bypassSecurityTrustHtml` used without DOMPurify on raw API content. Fix: wrap every `marked.parse()` with `DOMPurify.sanitize()`.
2. `services/projects.service.ts:85,111` — `http.get<any>` defeats TypeScript type safety on poll responses. Fix: use concrete return types.
3. `app.component.html:80` — inline `[style.display]` binding (convention violation). Fix: replace with `@if` or CSS class.
4. `app.component.html:287` — inline `[style.bottom]` binding (convention violation). Fix: use CSS modifier class.

**Warnings (should fix):**
5. `app.component.ts:274` — typo: `isAdditivOp` should be `isAdditiveOp`.
6. `app.component.ts:119` — `knownCount` is a plain field, should be a signal.
7. `styles.css` — missing styles for `text-ops-billing`, `sidebar-status-retry`, `error-state`.
8. `services/projects.service.ts:49` — constructor injection instead of `inject()`.
9. `index.html` — missing `crossorigin` on fonts.gstatic.com preconnect.
10. `app.component.ts:337` — `effect()` writes to signal without `allowSignalWrites: true`; should be `computed()`.

## Next steps

- Fix 4 critical issues before merge (XSS is highest priority)
- Run `/commit` to commit the UX polish changes
- Open PR targeting master
