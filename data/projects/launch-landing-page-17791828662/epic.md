# 🎯 Epic: Launch: Landing Page with CTA Funnel

## Business Value

The current landing page is an empty nginx shell with zero conversion path. Every visitor who arrives — from the relaunch post, from organic search, from a shared link — hits a dead end. This epic turns that dead end into the highest-leverage page in the product: the landing page becomes the product itself. The braindump editor is the hero. One click to a complete spec result. No signup wall, no explainer video, no "learn more" scroll. The visitor experiences the core value loop before they even know what the tool is called.

This is the proven pattern for developer tools: anonymous-first, try-before-signup. Competitors gate their product behind auth and onboarding flows, adding friction precisely where curiosity is highest. By making the landing page a live braindump editor with rotating demo content, spec-doc skips the entire "convince them to try it" phase. The product convinces by being used. Pre-computed mock responses for unedited demo braindumps mean this funnel costs nothing per visitor — no API calls burned on browsers, no infrastructure scaling concerns for launch traffic spikes.

This epic is the critical path to relaunch. The landing page URL is the only link in the relaunch post. Nothing else ships publicly until this funnel works end-to-end: visitor lands → sees braindump → clicks Analyze → sees complete spec output → hits conversion gate. Every other epic (BYOK, pricing, auth improvements) layers on top of this core loop. Ship this first, measure conversion, iterate everything else against real data.

## Scope

### What This Epic Covers

- **Braindump-as-hero landing page** — Static HTML page in `landing/` where the braindump textarea IS the entire above-the-fold experience, pre-filled with rotating demo content
- **Demo text rotation** — Multiple example braindumps cycling through the textarea with visible animation, showcasing different use cases (mobile app idea, SaaS feature, side project, refactoring task)
- **Single CTA click-to-result** — One button ("Analyze") that redirects to the app with all necessary context to render results immediately
- **Landing-to-app data handoff** — A defined contract for passing braindump content and mode (demo vs. custom) from the static landing page to the Angular app across the redirect boundary
- **App demo mode** — App detects demo mode on load, renders pre-computed analysis results instantly from static JSON without firing an API call
- **App real mode** — App detects custom braindump on load, fires the analysis API call, and shows the streaming/loading state through to the final result
- **Visual parity** — Landing page braindump textarea matches the app's newspaper design tokens, extracted into standalone CSS

### What This Epic Does NOT Cover

- ❌ **Pre-fired API calls from the landing page** — Requires cross-origin job tracking with no queue infrastructure; the app fires all API calls on its end. Re-scope only if measured latency proves unacceptable for conversion.
- ❌ **Shared component library between landing and app** — Static HTML cannot import Angular components. Design tokens are duplicated as plain CSS. Re-scope only if a third surface (docs, blog) needs the same tokens.
- ❌ **Conversion gate design and auth flow** — The gate ("Sign up to create your own") is a handoff point, not a deliverable of this epic. Its UX, copy, and auth integration are a separate scope.
- ❌ **Demo braindump content creation** — Writing four realistic braindumps and generating their cached JSON responses is content work, not engineering. Engineering consumes the JSON files; it does not produce them.
- ❌ **BYOK integration on the landing page** — If BYOK affects whether custom braindumps use the visitor's key vs. Sam's, that interaction is scoped separately. This epic assumes all landing-page-originated analysis uses the default key path.

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Design Token Extraction** — Extract newspaper design tokens from the app into standalone CSS that the static landing page can consume without Angular | None | With 2 | 0.5 days | High |
| 2 | **Landing-to-App Data Transfer Contract** — Define and implement the mechanism for passing braindump content and mode flag (demo vs. custom) across the redirect from landing to app, resolving the subdomain/origin constraint | None | With 1 | 1 day | High |
| 3 | **Landing Page Braindump UI** — Build the static HTML landing page with braindump textarea, demo text rotation animation, and CTA button wired to the data transfer contract | 1, 2 | With 4 | 2 days | High |
| 4 | **App Demo & Real Mode Integration** — App reads handoff data on load, renders pre-computed mock results for demo mode or fires the analysis API for real mode, ending at the conversion gate handoff point | 2 | With 3 | 2 days | High |

## Success Criteria

- ✅ Landing page loads in under 1 second on mobile (static HTML + minimal JS, no framework)
- ✅ Braindump textarea is the first and only thing visible above the fold — no scrolling required
- ✅ Demo braindumps rotate with visible text animation across at least 4 distinct examples
- ✅ One click from landing page to a complete spec result displayed in the app
- ✅ Demo mode renders the full pre-computed result instantly — no API call, no loading state
- ✅ Real mode (visitor-edited braindump) fires analysis and renders the result within normal analysis time
- ✅ Landing page textarea is visually indistinguishable from the app's braindump modal (newspaper token parity)
- ✅ Data handoff works reliably across the redirect — no content lost, no mode misdetection

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — Landing-to-app data flow, token extraction strategy, mock response schema
- [Timeline](./timeline.md) — Task status and execution tracking