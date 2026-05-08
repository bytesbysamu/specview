# 🔍 UX — Reader, Text Ops & Navigation — Analysis

## The Problem
The reader/text-ops UX has a structural inversion: triggers are at the bottom (floating toolbar) but results render at the top, status lives in two places, the home grid teaser shows meaningless first-100-chars, and category taxonomy is derived from project ID strings. The braindump proposes a sidebar-first command centre that would invert the trigger/result model and unify status, plus a deeper newspaper metaphor (datelines, pull quotes, breaking-news banner) and richer API-aware status semantics.

## Hard Constraints
- Stack is fixed: Angular standalone + signals, Flask backend, existing `app.component.html` and `styles.css` are the surfaces being reworked.
- The thread model lives in a separate braindump (`text-ops-thread-ui`) and is referenced as already-designed — this epic must not redesign it.
- `isBraindump()` is a known one-line bug (`!!currentSpec()`); fix is in scope, behaviour change is not.
- Newspaper editorial identity (Playfair / Source Serif / column grid) stays — no aesthetic redesign.
- Telegram 4096-char ceiling does not apply here (web reader only).

## Open Questions
- **Sidebar-first vs toolbar-first for AI ops** — braindump says move ops into the sidebar AND says the thread model fixes the inversion. Pick one: (a) ops migrate to sidebar, toolbar becomes result-only; (b) ops stay in toolbar, thread model handles placement; (c) both, phased.
- **Teaser source** — (a) smarter scan (first non-heading sentence), (b) AI-emitted `insight` field written during spec generation, (c) state-derived strings only. (b) requires a generation-pipeline change.
- **Section taxonomy** — replace ID-prefix `categorise()` with state-derived sections (Active / Ready to build / Specced / Braindumps / Archive)? Confirm these five are the canonical set.
- **Status bar verbosity** — show raw endpoint + job_id + attempt count to end users, or gate that behind a debug toggle?
- **File-switch with unsaved AI result** — prompt-to-confirm, auto-persist as draft, or keep current silent-clear?
- **Animation system** — Angular `@trigger` or CSS class toggles for the panel open animation?

## Dependencies & Sequencing
- Fix `isBraindump()` is independent and unblocks correct chip visibility everywhere else.
- Thread model (text-ops-thread-ui) must land before sidebar-first op migration is meaningful — otherwise result placement is still wrong.
- State-derived sections depend on a reliable per-project file-state classifier; that classifier also feeds teaser state strings and per-file status dots.
- AI-emitted `insight` field requires a spec-generation pipeline change before the grid can consume it — grid can ship with the scan-based fallback first.
- Unified status bar depends on the API exposing job_id, step, attempt, and elapsed in a consistent shape.

## Explicitly Out of Scope
- Thread model implementation — owned by `text-ops-thread-ui` braindump; reference only.
- Keyboard shortcuts / command palette / cross-project jump — second-pass per the braindump's own "fix first" list.
- In-file H2 section nav / TOC — second-pass.
- New project modal brainstorm helper — touches superpower-brainstorm wiring; separate epic.
- Diff-view redesign for rewriting ops — flagged as a problem but no concrete design committed; defer until thread model lands.
- Mobile / Ionic parity — this is the web reader only.