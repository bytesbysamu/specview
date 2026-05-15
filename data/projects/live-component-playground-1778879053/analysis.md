# 🔍 Live Component Playground — Analysis

## The Problem
The current design playground is 2,304 lines of frozen HTML — a screenshot, not a demo. It can't prove components actually work, respond to interaction, or render real data. Replacing it with live sub-components gives a working demo page and doubles as an integration smoke test.

## Hard Constraints
- All V2 sub-components must already exist and accept inputs as shown — this is composition, not creation
- No real AI calls, no real project creation, no Stripe flows (explicitly excluded)
- Must pass `ng build` with zero new test failures
- Files under 200 lines — one component + one demo-data file won't cut it; plan for 3-4 files minimum (component, template, demo data, possibly demo utils)

## Open Questions
- **Project grid data strategy**: Brain dump recommends "Option B anonymous, Option A logged in" — but success criteria says "no real API calls, works without auth." **Pick one.** Option B (hardcoded only) matches the stated constraints. Option A adds auth-gating complexity for a demo page.
- **Create modal behavior**: Section 7 says "opens the real create-project modal" and "Generate button works (if connected to real service)." The exclusions say no real project creation. **What does the modal actually do?** Options: (a) display-only with disabled submit, (b) functional form with a no-op submit handler, (c) cut the section entirely.
- **Old playground disposition**: Keep at `/playground-static` or delete? Decide before the PR, not during.
- **UsageMeterComponent**: Imported in the architecture sketch but has no playground section. Include it or remove the import?
- **Reader ↔ Sidebar binding**: When you click a file in the sidebar, does the reader panel update its content? If yes, you need multiple `DEMO_SPEC` entries keyed by filename — not one constant.

## Dependencies & Sequencing
- Every listed sub-component (`SectionNavComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `LandingPitchComponent`) must be stable standalone components with well-defined `@Input`/`@Output` contracts before this starts — verify first
- `marked` + `DOMPurify` must already be project dependencies (reader panel needs them)
- Route change (`/playground` → `LivePlaygroundComponent`) blocks on the old route being removable without breaking any navigation links elsewhere in the app or landing page

## Explicitly Out of Scope
- **Auth-gated real data path** — adds conditional logic, service injection, and error handling for a demo page. Re-scope if the playground becomes the primary onboarding funnel.
- **Real AI ops from playground** — cost and side-effect risk. Re-scope never; build a separate sandbox if needed.
- **Editable spec content** — turns a demo into a mini-IDE. Re-scope only if playground becomes a template-starter flow.
- **Animated transitions between sections** — not mentioned, don't add them. Re-scope if user testing shows confusion navigating the page.