# 🎯 Epic: UX: App Grid Polish

## Business Value

The project grid is the primary navigation surface of spec-doc — every session starts here. When all cards render identically (same static teaser, same monochrome appearance, same compressed padding) the tool creates friction at the moment it should create clarity. A solo founder context-switching across five live projects needs the grid to answer "where am I, what needs work" in under two seconds. Today it cannot do that.

Semantic color borders and real teasers transform the grid from a list of project names into a project dashboard: green means something is actively generating, blue means a spec is ready to implement, muted means a brain dump is waiting. That signal is free once the CSS variables are wired — it requires no new data, no new components, and no architectural change. The teaser fix closes the loop on existing logic that already fetches `braindump.md` content but discards it.

Breathing room compounds the value. Compressed cards at `12px 8px` make the grid feel like a file manager rather than a workspace. Increasing padding and grid spacing aligns the visual weight with the ClawBoi reference — the same restrained hierarchy that makes dense content scannable without requiring color overload.

## Scope

### What This Epic Covers

- **Real Braindump teasers** — Wire `leadFileContent` through `projectTeaser()` so Braindumps cards show the first real prose sentence from `braindump.md`, matching behavior already present in Specced and Ready-to-build sections
- **Semantic section color** — Left-border accent on `.file-item` keyed by `[attr.data-section]`; Active = green (`--status-running`), Specced = blue (`--accent`), Braindumps = muted (`--ink-muted`), Ready-to-build/Archive = transparent; section title tint for Active and Specced only
- **Card breathing room** — Base `.file-item` padding raised to `16px 12px`; negative-margin hover bleed updated to match; grid card override to flat `margin: 0; padding: 16px`; `minmax` widened to `260px`; section group gap increased to `32px`
- **CSS animation backport (5b, 5c, 5e)** — `@keyframes gen-shimmer` on `.gen-status-track` during active generation; `.diff-block-remove` / `.diff-block-add` highlight rules for unified diff output; `count-pulse` keyframe verification and fix — all `styles.css`-only

### What This Epic Does NOT Cover

- ❌ **Icon library evaluation (item 4)** — "Evaluate Lucide first" is research, not a deliverable; icon swap ships in its own epic once a library decision is confirmed
- ❌ **Retry button wiring (5d)** — Current render state is unknown; filed as a standalone bug investigation, not a polish task
- ❌ **Playground polish items 5f, 5g, 5i, 5j** — Medium/lower-impact patterns unrelated to grid polish; candidates for a dedicated playground-backport sprint
- ❌ **Items 5h and 5k** — Explicitly future/low-priority in the brain dump; no delivery pressure
- ❌ **Layout restructuring** — Column count, section grouping logic, and landing page are frozen
- ❌ **New components, services, or npm packages** — All changes are confined to existing files

## Tasks

| # | Task | Dependencies | Parallel With | Effort | Priority |
|---|------|--------------|---------------|--------|----------|
| 1 | **Card Breathing Room** | None | T2 | 0.5 days | High |
| 2 | **Real Braindump Teasers** | None | T1 | 0.5 days | High |
| 3 | **Semantic Section Color** | T1 (padding-left value must be settled before border offset is computed) | T4 | 1 day | High |
| 4 | **CSS Animation Backport** | None (pre-flight: verify `.gen-status-track`, `.gen-status-bar--active`, `.section-count-pulse`, and `@keyframes count-pulse` exist in `web-ng/src/styles.css` before editing) | T3 | 0.5 days | Low |

## Success Criteria

- ✅ No two Braindumps cards show identical teaser text when their `braindump.md` files contain distinct prose
- ✅ Braindumps cards fall back to `"Braindump — ready to generate"` only when `braindump.md` is empty or contains no non-heading prose
- ✅ Active section cards display a green left border; Specced cards display a blue left border; Braindumps cards display a muted left border; Ready-to-build and Archive cards display no border — verified in both grouped (all) view and single-section column view
- ✅ Section title color tint appears only for Active (green) and Specced (blue); remaining section titles are unstyled
- ✅ Dark mode renders all color rules correctly using existing CSS variables — no new palette additions
- ✅ Card content alignment is unchanged after border introduction — column cards: `padding-left: 9px` (12px base − 3px border); grid cards: `padding-left: 13px` (16px flat base − 3px border); no content shift in either view
- ✅ `.file-item` base padding is `16px 12px`; grid card override is `margin: 0; padding: 16px`; column hover bleed uses `0 -12px`
- ✅ `.gen-status-track` animates during active generation state; `.gen-status-bar--active` static track is replaced
- ✅ Diff output rendered by `diffHtmlUnified` displays red-tinted strikethrough on removed lines and green-tinted background on added lines
- ✅ `count-pulse` keyframe fires on section badge count changes; no silent mismatch between template class and CSS definition
- ✅ `ng build --configuration production` passes with zero errors before merge

## Related Documents

- [Analysis](./analysis.md) — Problems, open questions, and sequencing constraints driving this epic
- [Solution Architecture](./architecture.md) — Attribute-selector color strategy, grid vs. column card padding model, and CSS variable contracts
- [Timeline](./timeline.md) — Delivery status and task progress tracking