# 🏗️ Solution Architecture: SpecView Reddit Launch Recovery

## Architecture Overview

The Reddit launch data tells a clear architectural story: SpecView's *product* pipeline works, but there is no *conversion* pipeline. 618 views arrived and had nowhere to land — the static landing page has no call-to-action funnel, the privacy model is undefined, and the pitch speaks in features rather than pain. This architecture does not add product capabilities; it builds the missing conversion surface between "someone sees the post" and "someone uses the tool."

The core insight is that every piece already exists in the codebase but is wired for builder use, not visitor use. The chain adapter already abstracts AI providers — extending it to accept a user-supplied key is a configuration change, not a new system. The Angular app already has auth, signup, and a working spec generation flow. The `landing/` directory already serves static HTML through nginx. The architecture's job is to connect these existing pieces into a path that a skeptical Reddit visitor can walk in under 60 seconds: landing page → understand the pain → see it solved → try it themselves.

The design is intentionally minimal. No new services, no new databases, no analytics infrastructure. One static page revision, one privacy configuration path through the existing adapter, and one demo artifact. If this doesn't convert, the problem is still messaging — not architecture.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | BYOK key injection flows through the existing chain adapter; no new provider needed, just a key-source parameter |
| P2 — Thin HTTP Layer | Any new route for key validation is validate → check → respond; zero business logic in handlers |
| P4 — No Speculative Abstractions | One privacy model, one landing page, one demo, one subreddit. No multi-channel framework |
| P5 — OpenAPI-First | If a BYOK key-validation endpoint is added, it starts as a path in `openapi.yaml` before any handler exists |
| P7 — File Size & Structure | Landing page stays static HTML; no framework overhead for a page whose job is to load fast and convert |

## Component Design

### Privacy Model — BYOK-First with Hosted Trial

**Purpose**: Resolves the #1 unprompted objection (Fun-Foot711's comment) and unblocks all downstream copy.

The decision is a hybrid model weighted toward BYOK. Visitors who arrive from Reddit fall into two camps: those who will never paste proprietary ideas into a hosted tool (BYOK-only), and those who want to try before committing to anything (hosted trial). Serving only one camp loses the other.

BYOK is the *default* and the *marketed* position — "your key, your data, nothing stored." The hosted trial path exists as a friction reducer: a visitor can generate one spec using the server key without signup, seeing the real output before deciding whether to bring their own key. This is not a freemium tier; it is a single-use demonstration that the tool works.

The chain adapter already isolates all AI calls behind `adapter.py`. Supporting BYOK means the adapter accepts an optional key parameter and, when present, uses it instead of the server-configured key. The provider selection logic (`cli` vs `claude` vs `mock`) remains unchanged — BYOK only affects which API key is attached to the outbound call. No new provider module is needed.

Key storage is per-session only. The user's API key lives in the browser (sessionStorage, not localStorage) and is sent per-request via a header. The server never persists it. This is the strongest possible privacy stance and the simplest possible implementation.

### Landing Page — Static Conversion Surface

**Purpose**: Gives Reddit traffic somewhere to land with a single clear path to tool usage.

The landing page lives in the existing `landing/` directory and deploys as the same `nginx:alpine` container it already uses. It is pure static HTML and CSS — no Angular bundle, no JavaScript framework, no hydration delay. A Reddit visitor on mobile should see a fully rendered page in under one second.

The page has exactly three sections in a single scroll:

1. **Pain hook** — the specific "1–2 hours turning the mess in your head into something structured" pain point from Sam's Reddit comment, not a feature list
2. **Demo embed** — the single-workflow artifact showing a real braindump transformed into a structured spec (static media, not an interactive widget)
3. **CTA** — one button that routes to the Angular app's generation flow, with a secondary BYOK explanation link

The newspaper design tokens from `styles.css` are ported as standalone CSS variables into the landing page's own stylesheet. The landing page does not import or depend on the Angular build. Visual consistency is achieved through shared design tokens, not shared build artifacts.

### Conversion Funnel — Anonymous-First Entry

**Purpose**: Eliminates signup friction between "I'm curious" and "I see the value."

The funnel architecture is: **landing → anonymous generation → signup for persistence**. A visitor clicking the CTA arrives at the Angular app and can immediately paste a braindump and generate a spec. No account required. No API key required for this first generation (hosted trial path).

After generation completes, the visitor sees the full output and hits the conversion gate: "Sign up to save this spec and generate more" or "Bring your own API key for unlimited use." This is the only point where signup or BYOK configuration is required.

The Angular app already has the auth infrastructure (`auth.service.ts`, `token-lifecycle.service.ts`) and a signup page. The architectural change is making the generation flow accessible *before* auth, gating only persistence and repeat use. The `projects.service.ts` stores the anonymous spec in browser memory until signup, at which point it migrates to the server.

### Demo Artifact — Static Single-Workflow Capture

**Purpose**: Shows, don't tell. One complete transformation visible before any interaction.

The demo is a recorded artifact (animated screen capture or short video) embedded directly in the landing page. It shows a real braindump — messy, unstructured, the kind of notes a developer actually has — transformed into a structured spec with analysis, epic, and architecture sections. The entire capture runs under 60 seconds.

The artifact is a static file served from the `landing/` directory's public assets. No streaming, no player library, no external hosting. For maximum compatibility and instant playback, the primary format is a looping video element with a GIF fallback. File size target is under 5MB to avoid mobile load penalties.

The pitch rewrite (Task 3) determines *which* workflow to capture — the demo must match the specific pain point the pitch leads with, not showcase breadth.

### Relaunch Post — Single-Channel, Single-CTA

**Purpose**: One post on one subreddit, optimized for the rewritten pitch, with the landing page as the only link.

No new backend infrastructure is needed for the relaunch itself. The architectural constraint is that the landing page URL is the *only* link in the post — no direct links to the Angular app, no GitHub repo link, no "also check out" secondary CTAs. Every click goes through the conversion funnel.

The subreddit selection is a content decision, not an architectural one, but the architecture constrains it: the landing page must be the entry point, and the demo artifact must be embeddable or linkable from the post format the chosen subreddit allows.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Landing page | Static HTML/CSS in `landing/` on nginx:alpine | Sub-second load, no JS overhead, already deployed |
| Design tokens | CSS custom properties ported from `styles.css` | Visual consistency without build coupling |
| Demo artifact | Looping video / GIF, self-hosted | No external dependencies, instant playback, works in Reddit embeds |
| BYOK key transport | Request header per API call, sessionStorage on client | Never persisted server-side, strongest privacy guarantee |
| AI key routing | Existing `adapter.py` with optional key parameter | No new provider, no new abstraction — one parameter change |
| Auth gate | Existing JWT auth with deferred enforcement | Anonymous generation works; auth required only for persistence |
| Deployment | Existing Docker Compose + Coolify pipeline | No new containers, no new services |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| BYOK-first with single hosted trial | Addresses privacy objection head-on while preserving try-before-you-commit; strongest possible trust signal for dev audience | Hosted trial has cost exposure — one free generation per visitor. Acceptable at current traffic levels; add rate limiting if volume exceeds 100/day |
| Static landing page, not Angular route | Reddit visitors need sub-second load; SPA hydration adds 2–4 seconds on mobile. Static page also allows independent deploys without Angular build | Two stylesheets to maintain — landing CSS and `styles.css`. Mitigated by sharing token values, not files |
| Anonymous-first generation flow | Signup before value is the #1 conversion killer for dev tools. Showing real output before asking for anything builds trust | Anonymous specs exist only in browser memory — if the visitor closes the tab, the spec is lost. This is acceptable; the goal is conversion, not retention at this stage |
| Session-only key storage (no server persistence) | Eliminates the entire class of "what if your database leaks my API key" concerns. Also eliminates the need for key encryption infrastructure | Users must re-enter their key each session. Friction is real but acceptable — browser password managers auto-fill, and the privacy benefit outweighs the convenience cost |
| Single demo artifact, not interactive playground | The playground (`live-playground.component.*`) demonstrates design system capabilities, not the spec generation workflow. A recorded demo controls the narrative and guarantees the visitor sees the full transformation | A recording can't respond to "but what about my use case." Acceptable — the anonymous trial CTA immediately below the demo lets them try their own input |
| One subreddit, not multi-platform launch | The first post proved the channel works (618 views, 100% upvotes). Fix conversion on the proven channel before spreading to unproven ones | Slower total reach. Acceptable — 5 conversions from one post beats 0 from five posts |
| No analytics infrastructure in this iteration | The success metric is "≥5 users reach the tool within 48 hours." This is countable from server logs and signup records without dedicated analytics | No funnel drop-off data. Acceptable — if fewer than 5 convert, the problem is still obvious enough to diagnose without detailed metrics |

## Integration Points

The landing page connects to the Angular app via a single URL with an optional query parameter indicating the visitor arrived from the landing page. The Angular app reads this parameter to determine whether to show the anonymous generation flow or the standard authenticated flow.

The BYOK key header flows from Angular's `ai.service.ts` through the Flask API to `adapter.py`. The existing `require_auth` decorator in `modules/auth/` is bypassed for the single anonymous generation endpoint — a new decorator or a flag on the existing one controls this. All subsequent requests require auth as they do today.

No new inter-service communication is introduced. The landing page is a static site that links to the Angular app. The Angular app talks to the Flask API. The Flask API talks to the AI provider through the adapter. This is the same topology that exists today with one new entry point (the landing page CTA) and one relaxed constraint (anonymous first generation).

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking