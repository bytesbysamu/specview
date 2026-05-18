# exec-guide summary — UX Reader, Text Ops & Navigation

**Date:** 2026-05-08
**Tasks run:** 5 (exec-guide) + post-run fixes
**Tasks passed:** 5 / 5
**Tests:** passed (frontend: web-ng — 5 passed)
**Review:** 3 critical, 6 warnings (original) — several addressed in post-run fixes

---

## Original Tasks (exec-guide run)

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Quick Wins | ✓ complete | app.component.ts, styles.css, app.component.html |
| Task 2: Section Taxonomy + Teaser | ✓ complete | services/section-taxonomy.service.ts (new), services/project-teaser.ts (new), app.component.ts, app.component.html |
| Task 3: Sidebar-First Command Centre | ✓ complete | app.component.html, app.component.ts, styles.css |
| Task 4: Unified Status Bar + Per-File Dots | ✓ complete | app.component.ts, app.component.html, styles.css |
| Task 5: Panel Animation | ✓ complete | app.config.ts, app.component.ts, app.component.html |

---

## Post-Run Fixes (this session)

### Bug fixes

| Fix | Commit | Detail |
|-----|--------|--------|
| 404 on all AI op buttons | `2ed9af0` | Task 1 agent used wrong endpoint paths (`/api/operations/*-text`). Real paths are `/api/expand`, `/api/compress` etc. |
| Switch to generated API client | `7c72fdd` | `ai.service.ts` was using raw HttpClient. Switched to `ng-openapi-gen` generated functions (`brainstormText`, `expandText`, etc.) |
| Color system aligned | `e646c29` | Hardcoded hex values replaced with CSS tokens matching landing page (`--status-running`, `--status-success-bg`, font stacks) |
| Status bar location reversed | `2c6fe8f` | Epic had wrongly removed sidebar-status row and kept bottom bar. User's stated preference was the opposite. Fixed: bottom bar removed, sidebar-status row restored below file nav |
| Amber color too dark | `2c6fe8f` | `--status-running` changed from `#B8860B` (goldenrod) to `#F59E0B` (correct amber from braindump) |
| Idle dot color wrong | `2c6fe8f` | Idle state dot was green; should be neutral `var(--ink-muted)` |
| Theme toggle + logout in sidebar | `776e614` | Task 3 added duplicate controls to sidebar header. Removed — they already exist in masthead |
| Text op timeouts (skill timed out after 120s) | `776e614` | Two root causes: (1) `ThreadPoolExecutor` with `with` block was blocking HTTP thread after timeout fired; fixed with `shutdown(wait=False)`. (2) `--add-dir /data/spec-doc` was added to every CLI call including simple text ops, adding ~4s overhead and contributing to timeouts on large inputs. Now only added for chain-agent generation calls. Timeout bumped 120s → 300s. |
| Green status motif | `776e614` | Running/active state changed from amber to green (`#22A66A` / `#1DB97A` dark). `poll-pulse` glow updated. `.sidebar-status--active` border/bg now uses `var(--status-running)` |

### Partially addressed

- `sidebar-status` row moved to correct position (below file nav) but `inline-gen-status` bar (full dark strip in `expanded-main` during spec gen) not yet restored
- Theme toggle + logout in sidebar reverted; masthead versions still work

---

## Remaining to-do

### High priority

1. **Restore `inline-gen-status`** — full dark bar at top of expanded-main during spec generation (existed before exec-guide run; removed by Task 4). The sidebar dot row handles text ops; this bar handles spec gen.
2. **File switch warning** — switching files while an AI result is unsaved silently clears it (Problem #10 in braindump). Add a prompt or persist until dismissed.
3. **Op chip icons** — each chip should have a Lucide icon (expand → `arrow-up-down`, compress → `minimize-2`, etc.).

### Pre-merge code quality (critical from original review)

4. Add `section-taxonomy.service.spec.ts` — unit tests for `sectionFor()`.
5. Add `project-teaser.spec.ts` — unit tests for `projectTeaser()`, `firstNonHeadingSentence()`.
6. Update `ai.service.spec.ts` — cover generated-client shape.

### Warnings (from original review)

7. `app.component.ts:574` — `mode = computed(() => this.statusMode())` trivial passthrough; use `statusMode()` directly.
8. `app.component.ts:613` — `runOp(op as any)` — use proper union type.
9. `app.component.html` — `[style.bottom]` inline binding; replace with CSS class.
10. `app.component.ts` — `_syncElapsedTimer` setInterval missing `fakeAsync` spec.
11. `app.component.html` — New elements missing `data-test` attrs.

### Medium priority (newspaper polish / braindump items)

12. Spec file ordering — canonical reading order: braindump → analysis → epic → architecture → timeline → implementation-guide.
13. Dateline on spec files — `Generated 3 May 2026 · 94s · claude-sonnet-4-6`.
14. Section headers all-caps — "ACTIVE", "SPECCED", "BRAINDUMPS" in section nav.
15. Featured card — first card gets 2–3 sentence teaser.
16. Breaking news banner — temporary top banner when spec gen completes in grid view.
17. Undo prominence — Undo chip should be most visible element after Apply.

### Deployment

18. **Remote VPS has no project data** — `data/projects/` volume on VPS is empty; need to push data or recreate projects there.

---

## Next step

Run `/dev-review` on all changed files, then open PR from `ux/reader-textops-navigation` → `master`.
