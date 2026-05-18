# Leftover — UX Reader, Text Ops & Navigation

Things not done in this epic. Carry into next pass or a new epic.

---

## Code quality (pre-merge ideally)

**Replace Lucide CDN with lucide-angular npm package.**
Currently using a `<script src="https://unpkg.com/lucide@latest">` CDN tag + `createIcons()` called in Angular lifecycle. This is a DOM-scanning pattern that doesn't belong in Angular. `lucide-angular` npm package gives proper components, tree-shaking, no global. ~25 template occurrences to update. Also lets us delete the `_lucideScheduled` debounce hack we added.

**Add missing spec files for new services.**
Three services from exec-guide have no tests:
- `section-taxonomy.service.spec.ts` — unit tests for `sectionFor()` (5 branches: active job, implementation-guide, architecture/epic, braindump, archived)
- `project-teaser.spec.ts` — unit tests for `projectTeaser()` and `firstNonHeadingSentence()`
- `ai.service.spec.ts` — update to cover the ng-openapi-gen generated client shape (currently references deleted functions)

**Minor review warnings:**
- `app.component.ts` — `runOp(op as any)` should use an explicit union type
- `app.component.html` — `[style.bottom]` inline binding should be a CSS class
- `app.component.html` — missing `data-test` attrs on: status bar states, section group headers, file-dot elements
- `app.component.ts` — `_syncElapsedTimer` setInterval has no `fakeAsync` spec for clearInterval

---

## UX polish (newspaper / braindump vision)

**File switch warning.**
Switching files while an AI result is unsaved silently discards it. Should either: (a) prompt the user, or (b) persist the pending result and show it when they return to that file. Currently: result just disappears.

**Spec file canonical ordering.**
Sidebar file list uses API return order (alphabetical glob). Should be: braindump → analysis → epic → architecture → timeline → implementation-guide. Add a sort map in the frontend.

**Op chip icons.**
Op chips (Expand, Compress, Clarify, etc.) are text-only. Should have Lucide icons:
expand → `arrow-up-down`, compress → `minimize-2`, clarify → `help-circle`, simplify → `feather`, tldr → `align-left`, bullets → `list`, brainstorm → `sparkles`, style → `palette`.

**Dateline on spec files.**
Small metadata line at top of each rendered spec: `Generated 3 May 2026 · 94s · claude-sonnet-4-6`. Metadata is in git history; needs a backend endpoint or embed at generation time.

**Section headers all-caps.**
Section nav tabs ("Active", "Specced", etc.) should be all-caps newspaper style: "ACTIVE", "SPECCED", "BRAINDUMPS". CSS `text-transform: uppercase` already almost there — just needs the letter-spacing tightened to match the masthead's editorial feel.

**Featured card.**
First card in each section group gets a larger teaser (2–3 sentences from first paragraph), not just 1 sentence. Rest stay as 1-sentence teasers.

**Breaking news banner.**
When spec generation completes while user is in the grid (not in the expanded view), show a temporary top banner: "✦ ProjectName — spec generation complete". Fades after 4s. Currently only the file list refreshes silently.

**Undo prominence.**
After Apply, the Undo chip should be visually heavier than the other op chips — larger, or placed first, or with a distinct color. Currently same weight as Expand/Compress etc.

---

## Architecture / threading (separate epic)

**Thread / chain result model** (`text-ops-thread-ui` epic).
Text ops currently replace the visible content with a diff. The braindump described a threaded model: each op result is appended as a chain, user can branch, accept, or discard any node. This is a separate epic.

**Keyboard shortcuts.**
Escape = dismiss result, Cmd+Enter = apply, J/K = navigate files, / = search. None implemented yet.

**In-file H2 section nav / TOC panel.**
For long spec files, a floating TOC based on H2 headings. Lets you jump to "Architecture", "Data model" etc. without scrolling.

**Cross-project jump / command palette.**
Cmd+K opens a palette: recent projects, files, ops. Fuzzy search. Nice to have for power users.

---

## Remote deployment

**VPS data volume is empty.**
The Coolify deployment has a separate `data/` volume; it's empty on the remote. Either:
- Add a seed script that creates a demo project from a hardcoded braindump on first boot
- Document the manual upload path
- Build a project export/import endpoint so data can be pushed from local → remote
