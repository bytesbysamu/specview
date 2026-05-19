# Landing Page with CTA Funnel

## What this is

SpecView's Reddit post drove 618 views but there was no clear path from "I saw this post" to "I'm using the tool." The landing page either doesn't have a conversion funnel or the funnel is broken. This project builds (or rebuilds) the landing page as a single-purpose conversion surface: Reddit visitor lands, understands the pain, sees it solved, tries it themselves.

## The problem (from analysis)

> **Landing page exists?** The post drove 618 views but zero shares. Was there a link to a site, or did all traffic dead-end on the Reddit post? If no landing page, views are worthless.

> **What is the actual conversion funnel?** Reddit post -> ??? -> user pastes brain dump. The middle step is undefined.

> SpecView's r/SideProject debut pulled 618 views in 4 hours then flatlined to zero — no long-tail discovery.

## Architecture's landing page design (verbatim)

> The landing page lives in the existing `landing/` directory and deploys as the same `nginx:alpine` container it already uses. It is pure static HTML and CSS — no Angular bundle, no JavaScript framework, no hydration delay. A Reddit visitor on mobile should see a fully rendered page in under one second.

> The page has exactly three sections in a single scroll:

> 1. **Pain hook** — the specific "1-2 hours turning the mess in your head into something structured" pain point from Sam's Reddit comment, not a feature list
> 2. **Demo embed** — the single-workflow artifact showing a real braindump transformed into a structured spec (static media, not an interactive widget)
> 3. **CTA** — one button that routes to the Angular app's generation flow, with a secondary BYOK explanation link

> The newspaper design tokens from `styles.css` are ported as standalone CSS variables into the landing page's own stylesheet. The landing page does not import or depend on the Angular build. Visual consistency is achieved through shared design tokens, not shared build artifacts.

## Architecture's conversion funnel design (verbatim)

> The funnel architecture is: **landing -> anonymous generation -> signup for persistence**. A visitor clicking the CTA arrives at the Angular app and can immediately paste a braindump and generate a spec. No account required. No API key required for this first generation (hosted trial path).

> After generation completes, the visitor sees the full output and hits the conversion gate: "Sign up to save this spec and generate more" or "Bring your own API key for unlimited use." This is the only point where signup or BYOK configuration is required.

> The Angular app already has the auth infrastructure (`auth.service.ts`, `token-lifecycle.service.ts`) and a signup page. The architectural change is making the generation flow accessible *before* auth, gating only persistence and repeat use. The `projects.service.ts` stores the anonymous spec in browser memory until signup, at which point it migrates to the server.

## Architecture's design decisions (verbatim)

> **Static landing page, not Angular route** — Reddit visitors need sub-second load; SPA hydration adds 2-4 seconds on mobile. Static page also allows independent deploys without Angular build. Trade-off: Two stylesheets to maintain — landing CSS and `styles.css`. Mitigated by sharing token values, not files.

> **Anonymous-first generation flow** — Signup before value is the #1 conversion killer for dev tools. Showing real output before asking for anything builds trust. Trade-off: Anonymous specs exist only in browser memory — if the visitor closes the tab, the spec is lost. This is acceptable; the goal is conversion, not retention at this stage.

## Integration points (verbatim from architecture)

> The landing page connects to the Angular app via a single URL with an optional query parameter indicating the visitor arrived from the landing page. The Angular app reads this parameter to determine whether to show the anonymous generation flow or the standard authenticated flow.

> No new inter-service communication is introduced. The landing page is a static site that links to the Angular app. The Angular app talks to the Flask API. The Flask API talks to the AI provider through the adapter. This is the same topology that exists today with one new entry point (the landing page CTA) and one relaxed constraint (anonymous first generation).

## Technology stack (from architecture)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Landing page | Static HTML/CSS in `landing/` on nginx:alpine | Sub-second load, no JS overhead, already deployed |
| Design tokens | CSS custom properties ported from `styles.css` | Visual consistency without build coupling |
| Auth gate | Existing JWT auth with deferred enforcement | Anonymous generation works; auth required only for persistence |
| Deployment | Existing Docker Compose + Coolify pipeline | No new containers, no new services |

## What exists in the codebase

- `landing/` directory with nginx:alpine Dockerfile — already deployed
- `web-ng/src/styles.css` — newspaper design tokens
- `web-ng/src/app/services/auth.service.ts` — existing auth
- `web-ng/src/app/services/token-lifecycle.service.ts` — token management
- `web-ng/src/app/services/projects.service.ts` — project storage
- Docker Compose + Coolify deployment pipeline — already running

## Dependencies

- Depends on Task 1 (BYOK decision) — privacy stance determines landing page copy
- Blocks Task 5 (relaunch) — the landing page URL is the only link in the relaunch post

## Epic context

> **Task 2: Build landing page with CTA funnel** — Dependencies: Task 1 (privacy stance determines copy). Effort: 2 days. Priority: High.

> **Success criteria**: Landing page live with a single clear CTA that leads to tool usage.

## Review findings

- **Landing page IS confirmed to exist** — The analysis asks "Landing page exists?" as an open question, but `landing/` with nginx:alpine is verified in the codebase. The real question is whether it has a conversion funnel, not whether it exists.
- **Anonymous-first is the strongest idea** — Strategic review calls this "exactly right for dev tools." Let someone paste a braindump and see output before any signup.
- **Keep it static** — No Angular, no JS framework. Pure HTML/CSS. Sub-second mobile load.
