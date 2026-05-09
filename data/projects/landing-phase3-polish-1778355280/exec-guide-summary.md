# exec-guide summary — Landing Page Polish — Phase 3

**Date:** 2026-05-10
**Tasks run:** 5
**Tasks passed:** 5 / 5
**Tests:** passed (frontend: web-ng — 5 passed)
**Review:** 0 critical, 0 warnings (1 critical + 3 warnings found and fixed inline before merge)

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Security Gate | ✓ complete | app.component.ts, services/projects.service.ts |
| Task 2: Landing Markup Promotion | ✓ complete | landing/landing-v2.html, landing/style.css |
| Task 3: Landing Section Completion | ✓ complete | landing/landing-v2.html, landing/style.css |
| Task 4: App Correctness & Signal Hygiene | ✓ complete | app.component.ts, app.component.html, styles.css |
| Task 5: App Design Alignment | ✓ complete | app.component.ts, app.component.html, styles.css, word-count.pipe.ts (new) |

## Test results

frontend: web-ng — 5 passed, 0 failed

## Review findings

Issues found during review and fixed immediately:

1. `landing/landing-v2.html:444` — `update-banner-btn` class on `<a>` had no CSS rule. Fixed: removed the class (`.update-banner a` selector already covers it).
2. `landing/landing-v2.html:425-435` — Context cards grid used inline `style=` for the 3-column layout. Fixed: added `.context-grid` to `style.css`, removed all inline styles.
3. `web-ng/src/app/app.component.html:352` — `expanded-meta` guard was `@if (activeProject())` instead of `@if (activeProject() && currentSpec())`. Fixed: tightened guard.
4. `web-ng/src/app/app.component.ts:612` — `op as any` outside a catch block. Fixed: narrowed `toggleOp` parameter to the explicit union type.

## Changes summary

### App (web-ng)
- **XSS fixed**: All three `bypassSecurityTrustHtml` call sites now wrap `marked.parse()` with `DOMPurify.sanitize()`.
- **Type safety**: `http.get<any>` in `projects.service.ts` replaced with `PollStatusResponse` and `PollResultResponse` typed interfaces.
- **Signal hygiene**: `toolbarFloating` converted from `effect()`-driven `set()` to `computed()`. `pulsingSections` effect uses `allowSignalWrites: true`. `knownCount` converted from plain field to `signal(0)`.
- **Typo fixed**: `isAdditivOp` → `isAdditiveOp` across component and template.
- **Missing CSS added**: `.sidebar-status-retry`, `.error-state`, `.text-ops-billing`, `.expanded-meta` added to `styles.css`.
- **Op chip icons**: All op chips now have `<span class="btn-icon">` with Unicode glyphs (↕ ⊡ ? ◁ ≡ ≔ ✦ ◈).
- **Gen status bar unified**: `.inline-gen-status` replaced with `.gen-status-bar.gen-status-bar--active` — matches landing implementation.
- **Word count pipe**: New `WordCountPipe` standalone pipe; `expanded-meta` line shows `project name · N words` above the spec title.
- **Section group header**: `.section-group-header` border rule added to `styles.css`.

### Landing (landing/)
- **Inline styles purged**: `color:var(--border)` text corrected to `var(--ink-muted)`, opacity values removed, section-page inline overrides replaced with `.section-page--compact` class.
- **Button hierarchy**: Free tier CTA changed to `.btn-secondary`, Pro tier retains `.btn-primary`.
- **Pullquote bug fixed**: `class="pullquote-row pullquote-single"` split — single pullquote is now `.pullquote-single` only; a proper two-column `.pullquote-row` added after the comparison table.
- **Metrics bar**: Added between stat strip and "What ships" — full value prop in one line.
- **Aside-list**: Hero file-timing inline div cluster replaced with `<ul class="aside-list">`.
- **Context cards**: "Who it's for" section added with `.context-grid` wrapper and three `.context-card` entries.
- **Update banner**: `.update-banner` CSS ported from playground to `style.css`; banner added above footer.
- **`.section-page--compact`** modifier added to `style.css`.
- **`.update-banner`**, **`.gen-status-name`**, **`.context-grid`** added to `style.css`.

## Next steps

- Rebuild and deploy landing container: `docker compose build landing && docker compose up -d landing`
- Rebuild and deploy web container: `docker compose build web && docker compose up -d web`
- Verify dark mode on landing and app
- Open PR targeting master
