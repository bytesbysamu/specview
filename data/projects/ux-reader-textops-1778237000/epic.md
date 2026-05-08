# 🎯 Epic: UX — Reader, Text Ops & Navigation

## Business Value

Spec-doc's reader is the surface where Sam (and any future user) actually consumes the output of the spec pipeline. Today the reader has a structural inversion — triggers live at the bottom of the viewport while results render at the top — plus duplicated status, meaningless project teasers, and a category taxonomy derived from project ID strings. Every minute spent hunting for a result, re-reading a confusing teaser, or wondering whether the API is alive is a minute not spent shipping the project the spec describes. For a solo founder running six projects in parallel, that compounds.

The fix is not a redesign. The newspaper editorial identity (Playfair / Source Serif / column grid) already works and is a differentiator. What's missing is the editorial discipline: a single command centre (the sidebar), a single status indicator with real API semantics, state-derived sections that mean something, and teasers that surface the sharpest sentence rather than the first 100 characters. These changes turn spec-doc from a document viewer into a publication system for project thinking — the conceptual hook that makes spec-doc worth telling other founders about.

The buyer is Sam first; spec-doc is dogfooded daily across every active project. A reader that respects attention and surfaces system state honestly is the precondition for anyone else paying for it later.

## Scope

### What This Epic Covers
- **Sidebar-first command centre** — AI op chips migrate from the floating bottom toolbar into the sidebar; toolbar becomes result-display only (Apply / Copy / Dismiss). Resolves the trigger/result inversion.
- **Unified status bar with API semantics** — single bottom-fixed status bar showing connection state, current endpoint, job_id, step, attempt, elapsed; color-coded (green / amber / red / neutral); sidebar status row removed.
- **State-derived section taxonomy** — replace ID-prefix `categorise()` with five canonical sections: Active / Ready to build / Specced / Braindumps / Archive. Tab counts pulse on change.
- **Smarter project teaser** — scan-based first non-heading sentence as a fallback, plus state-aware variants ("Braindump — ready to generate", "generating architecture…", "Implementation guide ready · N tasks"). AI-emitted `insight` field deferred to a follow-up pipeline change.
- **Per-file status dots** — small yellow/green/red dot next to the filename in the sidebar when an op is running against that file, so status is visible even when scrolled away.
- **Panel open/close animation** — directional 250ms enter (sidebar staggers 40ms before main); 150ms reverse on close. Angular `@trigger` based.
- **`isBraindump()` one-line fix** — current `!!currentSpec()` is always true; correct to filename-equals-`braindump.md`. Brainstorm chip then only appears where it belongs.
- **Style chip placement fix** — presets render adjacent to the Style chip (inline in sidebar chip row), not at the top of the main content area.

### What This Epic Does NOT Cover
- ❌ **Thread/chain result model** — owned by `text-ops-thread-ui` braindump; this epic references it but does not implement result-adjacent rendering. Sidebar-first migration ships first; thread model lands in its own epic.
- ❌ **Keyboard shortcuts / command palette / cross-project jump** — second-pass per the braindump's own "fix first" list.
- ❌ **In-file H2 section nav / TOC panel** — second-pass.
- ❌ **New project modal brainstorm helper** — touches superpower-brainstorm wiring; separate epic.
- ❌ **Diff-view redesign for rewriting ops** — flagged as a problem, no concrete design committed; defer until thread model lands.
- ❌ **AI-emitted `insight` field in spec generation** — pipeline change scoped separately; this epic ships the scan-based fallback only.
- ❌ **Mobile / Ionic parity** — web reader only.
- ❌ **Newspaper deepening (datelines, pull quotes, breaking-news banner)** — aesthetic enhancements; out of MVP, revisit after structural fixes land.

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Quick wins: `isBraindump()` fix + weighted Apply button + Style chip placement** | None | — | 0.5 days | High |
| 2 | **State-derived section taxonomy + smarter teaser (scan-based)** | None | with 1 | 1 day | High |
| 3 | **Sidebar-first command centre (op chips migrate; toolbar = result-only)** | 1 | — | 2 days | High |
| 4 | **Unified status bar with API semantics + per-file status dots** | 3 | — | 1.5 days | High |
| 5 | **Panel open/close animation (Angular `@trigger`)** | 3 | with 4 | 0.5 days | Low |

## Success Criteria

- ✅ Clicking an AI op chip in the sidebar produces a result rendered in the main panel's toolbar/result area without the user's eye crossing the viewport — trigger and result occupy the same visual zone.
- ✅ Exactly one status indicator exists in the DOM at any time; the sidebar `sidebar-status` row is removed.
- ✅ Status bar in idle state shows `● connected · specview api · last sync Ns ago`; in active state shows endpoint, job_id, step, and elapsed seconds.
- ✅ Status bar color follows strict semantics: green (success flash), amber (in progress), red (failure / API unreachable, with retry), neutral (idle).
- ✅ Every project is classified into exactly one of Active / Ready to build / Specced / Braindumps / Archive based on its file state — no ID-prefix matching remains in `categorise()`.
- ✅ Tab count badges animate (single pulse) when their count changes due to a state transition.
- ✅ Project teaser shows a state-appropriate string: braindump-only projects show "Braindump — ready to generate"; in-progress projects show the live step; specced projects show the first non-heading sentence of the lead file.
- ✅ Sidebar file entry shows a yellow pulsing dot when an AI op is running against that file; turns green briefly on success or red on failure.
- ✅ `isBraindump()` returns true only when the open file's name is `braindump.md`; Brainstorm chip is hidden on all other files.
- ✅ Style chip presets render inline adjacent to the Style chip (in the sidebar chip area), not at the top of `.expanded-main`.
- ✅ Apply button is visually heavier than Copy and Dismiss (full-width or solid filled, distinct from ghost styling).
- ✅ Opening a project from the grid plays a 250ms directional animation (sidebar enters 40ms before main content); closing reverses in 150ms; no bounce or overshoot.
- ✅ All affected Angular components remain under 200 lines; `ng build --configuration production` passes before merge.

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking