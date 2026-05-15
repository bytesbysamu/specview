Now I have all the context I need. Here's the architecture document:

---

# 🏗️ Solution Architecture: Unified Page V3

## Architecture Overview

Unified Page V3 solves a visual identity crisis: spec-doc's three page sections — landing pitch, design playground, and app workspace — render as three unrelated products because V2's component refactor introduced a parallel CSS variable namespace (`--bg-primary`, `--text-primary`) that has no definition in the actual stylesheet. The newspaper design system defines `--ink`, `--bg`, `--serif`, `--sans`, and `--border`; V2's five sub-components reference none of them. The result is browser-default rendering wherever the design system should be speaking.

The architectural strategy is **V1's proven visual layer reassembled inside V2's component boundaries**. Rather than bridging two CSS universes with a token alias file, V3 ports V1's HTML structure — which was authored *for* the newspaper design system — into V2's five decomposed sub-components (`ProjectGridComponent`, `ReaderPanelComponent`, `SidebarV2Component`, `StatusBarComponent`, `SectionNavComponent`). Each component's scoped CSS file is emptied so `styles.css` governs all rendering through the global class names both versions already share (`.file-item`, `.expanded-sidebar`, `.section-nav`). Component-scoped styles return only for layout concerns that are genuinely local to a single component and have no global equivalent.

The critical prerequisite is fixing the upgrade button's `logout()` call before any visual work begins — a user who clicks "upgrade" and loses their session will never trust the product again, regardless of how it looks. The backend billing flow (`modules/billing/service.py` → `create_checkout_session`) already returns the correct Stripe Checkout URL with a `success_url` pointing to `/upgrade?session_id={CHECKOUT_SESSION_ID}`. The bug is entirely frontend: the click handler invokes the auth service's logout method instead of navigating to the billing checkout endpoint. This is a one-line wiring fix, but it must ship and soak before V3 visual work touches the same component tree.

## Design Principles

| Principle | Application in V3 |
|---|---|
| **P4 — No Speculative Abstractions** | No token alias file (`_token-bridge.css`). Port V1's HTML directly into V2 component boundaries instead of maintaining two CSS variable namespaces with a bridge layer. The bridge is speculative — V1's class names already work with `styles.css` and the HTML is structurally identical. |
| **P7 — File Size & Structure** | V2's decomposition into 5 sub-components already satisfies this. V1's monolithic `app.component.html` (585 lines) stays dead; its markup is distributed across the sub-components, each well under the 200-line target. |
| **P5 — OpenAPI-First** | The billing checkout flow is already contract-driven: `POST /api/billing/create-checkout-session` returns `{ url }`. The frontend fix wires the upgrade button to this existing endpoint rather than inventing a new one. |
| **P1 — Adapter Boundary** | No new adapters needed. The billing service (`modules/billing/service.py`) is already the sole Stripe adapter. All AI calls continue through `modules/runtime/chain/adapter.py`. V3 is a pure frontend architecture change. |
| **Single source of CSS truth** | `styles.css` is the design system. Component `.css` files are empty by default. Scoped styles are added back only when a component needs layout that has no global equivalent — and each addition requires justification. |
| **Escape hatch over big bang** | V1 remains untouched at `/v1` for the entire soak period. The route cutover is a swap, not a deletion. Dead code cleanup is a separate task gated on one week of zero rollbacks. |

## Component Design

### Upgrade Button Fix (Task 1 — prerequisite)

**Purpose**: Restore trust at the payment boundary before any visual refactoring.

The upgrade button in V2's app workspace currently calls the auth service's `logout()` method instead of initiating the Stripe Checkout flow. The backend is correct: `POST /api/billing/create-checkout-session` returns a `{ url }` payload pointing to Stripe's hosted checkout page, with `success_url` configured to redirect back to `/upgrade?session_id={CHECKOUT_SESSION_ID}` and `cancel_url` to `/upgrade`. The `GET /api/billing/verify-session?session_id=` endpoint already resolves the plan state on return.

The fix is a frontend wiring change: the upgrade button's click handler must call the billing service's checkout method and navigate to the returned URL. No new endpoints, no new services, no backend changes. The existing `@require_auth` decorator on the billing route ensures only authenticated users can initiate checkout. This ships as an independent PR and soaks before V3 visual work begins, because the upgrade button lives in the same component tree that Phase 2 will be rewriting.

### CSS Strategy: Global Cascade, Not Token Bridge

**Purpose**: Eliminate the visual disconnect between the three page sections with the simplest possible intervention.

Two strategies were evaluated for resolving the CSS token mismatch:

**Option A — Token alias file** (`_token-bridge.css`): Maps V2's variable names to V1's design tokens (e.g., `--bg-primary: var(--bg)`). Allows V2's component CSS to remain unchanged.

**Option B — Empty component CSS, port V1 HTML** (chosen): Clears all five V2 component CSS files. Ports V1's HTML structure (which was authored for the newspaper design system's class names) into V2's component templates. `styles.css` handles all styling through the same global classes V1 used.

Option B wins because the HTML comparison confirms both versions use identical class names (`.file-item`, `.file-item-title`, `.file-item-teaser`, `.file-item-meta`, `.expanded-sidebar`, `.section-nav`). The visual difference is purely CSS specificity — V2's component-scoped selectors override the global ones. Emptying the component CSS files removes the overrides and lets the global design system render correctly. The token bridge (Option A) would paper over the mismatch while leaving two parallel CSS naming conventions in the codebase permanently — a maintenance burden with no upside once the HTML is aligned.

Component-scoped CSS returns only for genuinely local layout concerns: flex containers internal to a single sub-component that have no global equivalent. Each such addition must be documented with a comment explaining why it cannot live in `styles.css`.

### V1 HTML Porting into V2 Component Boundaries

**Purpose**: Distribute V1's 585-line monolithic template across V2's five sub-components while preserving the newspaper design system's rendering.

The five V2 sub-components map to clear regions of V1's `app.component.html`:

| V2 Component | V1 Region | Key Elements Ported |
|---|---|---|
| `ProjectGridComponent` | The 4-column newspaper grid | `.file-item` cards with `20px 24px` padding, `282px` column width, section groups with separators, featured/teaser layout, search bar with left-aligned project count |
| `ReaderPanelComponent` | Expanded file viewer | `.expanded-main`, `.markdown-content`, `WordCountPipe` integration, `DOMPurify` sanitization |
| `SidebarV2Component` | File list in expanded mode | `.expanded-sidebar`, `.sidebar-file` list, active-file highlighting |
| `StatusBarComponent` | Generation status strip | Dark olive background, white text, project name, current step, elapsed timer |
| `SectionNavComponent` | Spec section navigation | Pill buttons with count badges, active underline indicator |

V2's masthead stays as-is — the user confirmed it already looks correct. The masthead is the persistent frame that creates visual continuity between the landing pitch and the app workspace; it provides the "you're still in the same product" signal that V2's app section currently lacks.

Two V1 features missing from V2 require explicit porting:

**Panel slide animation** (`@panelEnter`): V1's expanded view transitions in with a slide animation. This must be registered in the V2 component that hosts the reader panel, using Angular's `@trigger` animation syntax. The animation definition ports from V1's `app.component.ts` to the V2 host component.

**Usage meter**: V1 renders a usage meter in the masthead area. V2's masthead component needs this data binding added. The billing status endpoint (`GET /api/billing/status`) already returns `plan` and `status` — the usage meter reads from the same subscription signal the rest of the auth-conditional UI uses.

### Auth-Conditional Page Sections

**Purpose**: Make the single-route architecture work for both anonymous visitors and authenticated users without a jarring re-render.

The unified page renders three sections in a single vertical scroll:

1. **Landing pitch** — visible to anonymous users, collapsed or hidden for authenticated users
2. **Design playground** — visible to anonymous users as a live demo; hidden or collapsed for authenticated users (transforming it into a "new project" workspace is explicitly out of scope for V3)
3. **App workspace** — visible only to authenticated users (newspaper grid, reader panel, sidebar, status bar, section nav)

The transition between anonymous and authenticated states uses Angular's `@if` control flow bound to the auth signal. No CSS-only transitions, no route changes, no page reloads. The auth signal already exists in `app.component.ts` and V2 already uses `@if` blocks for conditional rendering — V3 only changes *what* renders in each block, not the mechanism.

For authenticated users, the landing pitch and playground sections collapse. The app workspace fills the viewport. The masthead persists across both states, providing the visual continuity that makes the state change feel like a reveal rather than a navigation.

### Test Migration Strategy

**Purpose**: Ensure the 155 existing Karma tests pass against V2's component structure without regressing V1.

The test migration has three layers:

**Layer 1 — Existing tests against V2 DOM**: The 155 Karma unit tests currently test V1's `AppComponent`. Because V2's sub-components use the same class names and `[data-test]` attributes, most tests should pass with import changes only (pointing test beds at V2's component tree). Tests that query the DOM by component-internal structure (not `[data-test]` selectors) will need selector updates.

**Layer 2 — Sub-component unit tests**: Each of V2's five sub-components gets its own spec file following the project's testing conventions: Jasmine spy mocks via `createMock{Name}Service()` factory files, `fakeAsync` for any polling, `[data-test]` selectors only. These tests verify the component's input/output contract in isolation.

**Layer 3 — E2E against both routes**: During the transition period, the E2E suite runs against both `/` (V2) and `/v1` (V1). Any test that passes on `/v1` but fails on `/` indicates a V2 component bug. This asymmetric test gate prevents premature route commitment.

### Route Cutover Architecture

**Purpose**: Swap V2 to `/` with a zero-risk rollback path.

The cutover modifies `app.routes.ts` (which currently maps `/` to V1's `AppComponent`) to serve V2's `AppV2Component` at `/` and V1's `AppComponent` at `/v1`. Both route entries point to fully independent component trees — no shared mutable state between them. The `/v1` escape hatch exists for exactly one purpose: if any user-facing bug appears on `/` post-cutover, `/v1` is a known-good fallback that requires zero code changes to reach.

The escape hatch has a defined lifetime: one week from route swap with zero rollbacks triggers Task 5 (dead code cleanup). The `/v1` route, V1's `app.component.html`, any V1-only CSS classes in `styles.css`, and duplicate imports are removed. `styles.css` itself is never deleted — it is the design system. All shared services (`ProjectsService`, auth, billing, subscription, token lifecycle) are never touched — they serve both V1 and V2 identically.

## Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend framework | Angular 17 (existing) | Signal-based reactivity, `@if`/`@for` control flow, standalone components — all already in use. No framework changes for V3. |
| Styling | Global `styles.css` (existing newspaper design system) | V1's CSS custom properties (`--ink`, `--bg`, `--serif`, `--sans`, `--border`) are the product's visual identity. V3 removes the competing variable namespace, not adding a bridge. |
| Component architecture | V2's 5 sub-components (existing) | `ProjectGridComponent`, `ReaderPanelComponent`, `SidebarV2Component`, `StatusBarComponent`, `SectionNavComponent` — already decomposed and working. V3 changes their templates and empties their CSS, not their TypeScript contracts. |
| Animation | Angular `@trigger` animations (existing in V1) | `@panelEnter` slide animation ports from V1's component to V2's reader panel host. No third-party animation library. |
| Backend | Flask API at `:5001` (unchanged) | V3 is a pure frontend architecture change. No new endpoints, no service modifications. Billing checkout (`/api/billing/create-checkout-session`) and billing status (`/api/billing/status`) already exist and are correct. |
| Testing | Karma + Jasmine (unit), Playwright (E2E) — existing | Test migration repoints existing specs at V2 components. No test framework changes. |
| Build verification | `ng build --configuration production` | Required to pass at every phase boundary per P7. Catches template errors, missing imports, and dead code references that runtime wouldn't surface until user interaction. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|---|---|---|
| **Port V1 HTML into V2 components** instead of reskinning V2 HTML with V1 tokens | V1's HTML was written *for* the newspaper design system — its class names, nesting structure, and semantic grouping match `styles.css` exactly. V2's HTML was extracted from the design playground, which used different padding, border, and grid assumptions. Reskinning would require auditing every element; porting replaces wholesale. | Requires rewriting V2 component templates (one-time cost). Any V2-only template features (e.g., new conditional blocks) must be re-added after porting. |
| **Empty component CSS files** instead of token alias bridge | The bridge (`_token-bridge.css`) would maintain two naming conventions permanently. Emptying CSS files is simpler, has no ongoing maintenance cost, and works because both versions share class names. Component CSS returns only with documented justification. | Loses the ability to override global styles per-component without touching `styles.css`. Acceptable because the design system should be centralized. |
| **Fix upgrade bug first** (Task 1) before visual work (Task 2) | The upgrade button is in V2's component tree. Visual refactoring will rewrite templates in that tree. Fixing the bug first means the fix ships in a known-good template, and the visual refactor doesn't accidentally re-introduce the bug by porting from V1 (which may not have the fix). | Delays visual work by half a day. Worth it: shipping a visual upgrade while the payment flow is broken sends the wrong signal. |
| **Hide playground for auth users** instead of transforming it into "new project" workspace | Transforming the playground is feature work disguised as refactoring. V3's scope is visual parity and route cutover. The playground-to-workspace conversion requires localStorage persistence, auth-triggered migration, and a rethought onboarding flow — all explicitly out of scope. | Authenticated users lose visibility of the playground demo. Acceptable: they already have the real app workspace. Revisit post-cutover when V3 is stable for 2+ weeks. |
| **`@if` conditional rendering** instead of CSS-only show/hide for auth state | `@if` removes DOM nodes entirely for the hidden state, keeping the component tree clean and avoiding style leakage from invisible sections. CSS-only (`display: none`) leaves the DOM populated, which can interfere with accessibility, SEO, and `[data-test]` selector uniqueness in E2E tests. | Initial render for authenticated users must wait for the auth signal to resolve before showing the app workspace (brief flash). Mitigated by the masthead rendering immediately in both states. |
| **One-week soak with `/v1` escape hatch** before dead code cleanup | Removing V1 files is irreversible in production perception (git can restore, but users can't). A week of parallel operation catches edge cases (specific project structures, unusual viewport sizes, accessibility tool interactions) that automated tests miss. | Maintains two component trees for a week, increasing the chance of a confusing divergence if a hotfix is needed. Mitigated by freezing V1 — no changes to `/v1` during soak. |
| **No new backend endpoints or services** | The billing backend is already correct: checkout session creation, webhook handling, session verification, and portal session creation all work. The usage meter reads from `GET /api/billing/status`. V3's architecture change is entirely within `web-ng/src/app/`. | If a future V3 feature (e.g., playground braindump persistence) needs backend support, it requires a separate task. Acceptable: that feature is explicitly out of V3 scope. |
| **Screenshot overlay at 50% opacity as acceptance test** | Pixel-parity is the core success criterion. Automated visual regression tools add infrastructure complexity for a one-time comparison. A manual overlay (V1 screenshot layered over V2 at 50% opacity in any image editor) catches grid alignment, card sizing, font rendering, and spacing mismatches faster than writing custom visual diff tooling. | Not automated — must be repeated manually after each visual change. Acceptable for a 1.5-day visual parity phase; would not scale for ongoing visual regression. |

## Risk Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| V1 HTML porting misses a V2-only feature (e.g., a new `@if` block or signal binding added after V2's initial build) | Feature regression visible only to users who trigger the specific flow | Diff V1 and V2 templates before porting. Any V2-only logic block must be explicitly carried forward into the ported template. Build verification (`ng build --configuration production`) catches missing signal references at compile time. |
| Global `styles.css` has classes that collide across the landing pitch, playground, and app workspace sections | Unintended style inheritance between sections | The landing pitch uses `landing/style.css` (isolated). The playground loads CSS via `fetch` (Shadow DOM or scoped `<style>`). Only the app workspace uses `styles.css` classes. Collision risk is between playground and app — which is actually the *desired* outcome (same visual language). |
| The 155 existing Karma tests break because they query V1-specific DOM structure | Test suite blocks the build, delaying route cutover | Layer the migration: first run existing tests against V2 to identify failures, then fix selectors (preferring `[data-test]` attributes over structural queries), then add sub-component tests. Never delete a passing test — only repoint it. |
| Upgrade button fix introduces a session-handling regression | Users lose auth state during checkout flow | The fix is a wiring change (click handler target), not a session flow change. The `@require_auth` decorator on the billing endpoint already validates the JWT. The Stripe `success_url` returns to the SPA, which re-reads the auth signal on load. Verify with a manual flow: click upgrade → complete Stripe test checkout → confirm return to `/upgrade` with session intact. |

## Related Documents

- [Analysis](./analysis.md) – CSS token misalignment root cause, V1 vs V2 computed style comparison, and the dependency sequencing that makes the upgrade fix a prerequisite
- [Epic](./epic.md) – Scope boundaries, 5-task breakdown, success criteria, and explicit exclusions (playground persistence, live front page, speculative token bridge)
- [Timeline](./timeline.md) – Phase-by-phase execution tracking across the 4-day budget plus 1-week soak period