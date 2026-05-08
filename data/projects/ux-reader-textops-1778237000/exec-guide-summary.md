# exec-guide summary — UX Reader, Text Ops & Navigation

**Date:** 2026-05-08
**Tasks run:** 5
**Tasks passed:** 5 / 5
**Tests:** passed (frontend: web-ng — 5 passed)
**Review:** 3 critical, 6 warnings

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Quick Wins | ✓ complete | app.component.ts, styles.css, app.component.html |
| Task 2: Section Taxonomy + Teaser | ✓ complete | services/section-taxonomy.service.ts (new), services/project-teaser.ts (new), app.component.ts, app.component.html |
| Task 3: Sidebar-First Command Centre | ✓ complete | app.component.html, app.component.ts, styles.css |
| Task 4: Unified Status Bar + Per-File Dots | ✓ complete | app.component.ts, app.component.html, styles.css |
| Task 5: Panel Animation | ✓ complete | app.config.ts, app.component.ts, app.component.html |

## Test results

Tests: passed (frontend: web-ng — 5 passed)

## Review findings

### Critical (must fix before merge)

- `services/section-taxonomy.service.ts` — No spec file. Unit tests for `sectionFor()` required.
- `services/project-teaser.ts` — No spec file. `projectTeaser()`, `firstNonHeadingSentence()`, `countTasks()` untested.
- `services/ai.service.ts` — Spec not updated. Now uses generated API client; mock+spec need to reflect new shape.

### Warnings (should fix)

- `app.component.ts:574` — `mode = computed(() => this.statusMode())` trivial passthrough; reference `statusMode()` directly.
- `app.component.ts:613` — `runOp(op as any)` — use proper union type.
- `app.component.html:246` — `[style.bottom]="..."` inline style binding; replace with CSS class.
- `app.component.ts` — `_syncElapsedTimer` setInterval has no `fakeAsync` spec for clearInterval.
- `app.component.html` — New elements (section groups, file-dot, status bar states) missing `data-test` attrs.

---

## Braindump review — what was done vs what was asked

### Colors

| Token | Braindump said | Implemented | Status |
|-------|---------------|-------------|--------|
| Amber / in-progress | `#F59E0B` | `--status-running: #B8860B` (darker goldenrod) | ⚠ wrong shade — braindump specified brighter amber |
| Green / success | `#2E7D32` forest green | `--status-success-bg: #2E7D32` | ✓ |
| Red / failure | `var(--red)` | `var(--status-failure)` → `var(--red)` | ✓ |
| Neutral / idle | default ink | `--status-idle` dark green text | ⚠ idle should be neutral ink, not green |

**Fix:** Change `--status-running` to `#F59E0B` (light) / `#D97706` (dark). Change `--status-idle` text color to `var(--ink-muted)` not green — idle means nothing is happening.

### Status bar location — CONFLICT

Braindump explicitly said: **"The sidebar status row is the right home for live status. Keep sidebar-status below the file nav. Remove the fixed bottom viewport bar."**

User also confirmed in session: *"i actually like the status bar just below the nav, we keep that one."*

What was implemented: **bottom fixed bar kept, sidebar-status row removed** (the epic reversed the user preference).

**Fix:** Add sidebar-status row back below the file nav. Show idle/active/failure state inline. Keep bottom bar as secondary (or remove it). This is a meaningful reversal of Task 4.

### Button consolidation — what was done

| Location | Before | After | Status |
|----------|--------|-------|--------|
| Op chips (Expand/Compress/etc.) | Floating bottom toolbar | Sidebar ✓ | ✓ done |
| Style presets | Top of expanded-main | Sidebar below Style chip ✓ | ✓ done |
| Result toolbar | Chips + Apply/Copy/Dismiss mixed | Apply/Copy/Dismiss only ✓ | ✓ done |
| Generate Specs / Generate Guide | Sidebar | Sidebar | ✓ unchanged |
| Undo / Redo | Toolbar | Sidebar chip row | ✓ done |

Op chips have no Lucide icons — just text labels. Braindump implied icons would match the app's icon language (now Lucide). Minor gap.

---

## Things to do — from braindump, not yet implemented

### High priority (breaks user expectations)

1. **Status bar location** — restore sidebar-status row; it is the stated preference. The bottom bar was the one to remove, not the sidebar one.
2. **Amber color** — change `--status-running` from `#B8860B` to `#F59E0B` (light) / `#D97706` (dark). Current value is too dark, reads as brown not amber.
3. **Idle status color** — idle state should use `var(--ink-muted)` (neutral), not green. Green = success, not idle.
4. **File switch warning** — switching files while an AI result is unsaved silently clears it (Problem #10 in braindump). Add a prompt or persist the result until explicitly dismissed.
5. **Op chip icons** — each chip should have a Lucide icon matching its action (e.g. `expand` → `arrow-up-down`, `compress` → `minimize-2`, `list` → `list`, `zap` → `zap`, etc.).

### Medium priority (newspaper analogy + polish)

6. **Spec file ordering** — sidebar file list should show files in canonical reading order: braindump → analysis → epic → architecture → timeline → implementation-guide. Currently uses API return order.
7. **Dateline on spec files** — small line at top of each spec: `Generated 3 May 2026 · 94s · claude-sonnet-4-6`. Metadata exists in git history; surface it.
8. **Section headers all-caps** — newspaper style: "ACTIVE", "SPECCED", "BRAINDUMPS" etc. in the section nav tabs.
9. **Featured card** — first card in each section gets larger teaser (2-3 sentences / first paragraph), not just 1 sentence.
10. **Breaking news banner** — when spec generation completes while user is in the grid, temporary top banner: "✦ ProjectName — spec generation complete". Fades after 4s.
11. **Undo prominence** — after Apply, the Undo chip/button should be the most visible element. Currently it appears in the chip row with the same weight as other ops.

### Lower priority / second pass (explicitly deferred in epic)

12. Thread/chain result model → `text-ops-thread-ui` epic (separate).
13. Keyboard shortcuts (Escape=dismiss, Cmd+Enter=apply, J/K=files, /=search).
14. In-file H2 section nav / TOC panel.
15. Cross-project jump / command palette (Cmd+K).
16. Brainstorm helper in new project modal.
17. Op chips as a collapsed "AI ▾" menu for non-brainstorm files.
18. Pull quotes in project cards (best sentence, not first sentence).

### Pre-merge code quality

19. Add `section-taxonomy.service.spec.ts` with unit tests for `sectionFor()`.
20. Add `project-teaser.spec.ts` with unit tests for `projectTeaser()` and `firstNonHeadingSentence()`.
21. Update `ai.service.spec.ts` to cover generated-client shape.
22. Replace `[style.bottom]` inline binding with a CSS class.
23. Fix `runOp(op as any)` — use explicit union type.
24. Add `data-test` attrs to status bar states, section group headers, file-dot elements.
