# 🔍 Unified Page V3 — Analysis

## The Problem
The V2 rewrite achieved clean component decomposition (5 sub-components with proper I/O contracts) but broke visual coherence — its components reference undefined CSS variables (`--bg-primary`, `--text-primary`) instead of the newspaper design system tokens (`--ink`, `--bg`, `--serif`). The result is three visually disconnected sections glued onto one page. V3 must merge V1's proven visual rendering with V2's architecture without regressing either.

## Hard Constraints
- V1 stays untouched at `/` until V2 reaches pixel-parity — no exceptions
- 155 Karma unit tests + E2E suite must pass on both routes during transition
- `ng build` must pass at every phase boundary
- No new dependencies (no Redis, no Postgres, no external queue)
- Solo dev — 4-day budget + 1-week buffer; phases must be sequential and independently shippable

## Open Questions
- **Which masthead?** Brain dump says "keep V2's masthead (looks good)" AND "keep V1's masthead with edition, date, title, tagline." V2's masthead is described as missing entirely in the screenshot analysis. → Pick one, screenshot both, decide before Phase 1.
- **CSS strategy: empty files vs. token bridge vs. port V1 HTML?** Three mutually exclusive approaches appear: (1) empty V2 CSS files, rely on global styles; (2) create `_token-bridge.css` mapping `--bg-primary → var(--bg)`; (3) port V1's HTML wholesale into V2 component boundaries. The recommended option (B: port V1 HTML) contradicts the implementation plan (empty CSS files). → Decide before writing any CSS.
- **Auth transition UX?** Options: `@if` swap, CSS slide transition, or collapsible pitch section. No decision made. → Blocks the landing-pitch component's HTML structure.
- **Playground fate for logged-in users?** Hide / collapse / transform into "new project" flow. → Blocks route and template design. Recommendation (Option C: transform) is a product feature, not a refactor — see scope below.

## Dependencies & Sequencing
- **Logout bug fix** → blocks everything. Users clicking "upgrade" get logged out. Ship before any visual work.
- **Masthead decision** → blocks Phase 1 CSS work (determines which header HTML lives in which component).
- **CSS strategy decision** → blocks Phase 1 entirely. Emptying files vs. porting HTML vs. token bridge produce different component templates.
- **Phase 1 (visual parity)** → blocks Phase 2 (test migration targets the final DOM structure).
- **Phase 2 (tests green)** → blocks Phase 3 (route cutover).
- **Phase 3 + 1 week soak** → blocks Phase 4 (dead code cleanup).

## Explicitly Out of Scope
- **Playground braindump → first project auto-migration on signup** — backend feature (localStorage persistence, auth-triggered migration). Revisit after V3 ships and route cutover is stable.
- **"Live front page" / scroll-driven narrative / progressive disclosure sections** — product redesign, not a refactor. Revisit as V4 after V1 retirement completes.
- **"Kill the playground as a separate concept"** — requires rethinking onboarding flow; out for V3. Trigger: V3 stable for 2+ weeks with no rollbacks.
- **Transforming playground into "new project" workspace for auth users** — feature work hiding inside a refactor. For V3, just hide or collapse it. Revisit post-cutover.
- **Token alias file (`_token-bridge.css`)** — only relevant if the CSS strategy decision picks option 2. Do not build speculatively.