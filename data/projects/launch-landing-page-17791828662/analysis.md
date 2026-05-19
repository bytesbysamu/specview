# 🔍 Launch: Landing Page with CTA Funnel — Analysis

## The Problem
The current landing page is a deployed nginx:alpine shell with no conversion path. Visitors have no way to experience the product without signing up first. This replaces it with a zero-friction funnel: the landing page becomes a live braindump editor that feeds directly into the app, demoing the product by being the product.

## Hard Constraints
- Landing page must stay in `landing/` as static HTML + minimal JS on nginx:alpine — no Angular, no Node runtime
- No Redis, no external queue — rules out any job-queue pattern for pre-fired API calls
- Braindump modal design must match app's newspaper tokens — but can't share Angular components across static HTML, so tokens get duplicated as plain CSS
- Blocks the relaunch (Task 5) — this ships before anything goes public
- Depends on Task 1 (BYOK) — though the dependency is unclear given there's no marketing copy to adjust (see Open Questions)

## Open Questions
- **How does custom braindump text travel from landing → app?** Brain dump lists three options (URL param, sessionStorage, POST) without deciding. sessionStorage won't survive a cross-origin redirect if landing and app are on different subdomains. URL param has length limits. → **Decision needed before architecture.**
- **Fire API from landing page or let the app do it?** Brain dump proposes both, then admits the second is "simpler, slightly slower." Given no-queue constraint, firing from landing requires CORS setup and a way for the app to retrieve the result. Letting the app fire on load is simpler and stays within existing infra. → **Pick one.**
- **What exactly depends on BYOK (Task 1)?** The spec says "privacy stance determines landing page copy" but also says there IS no copy — just a textarea and a button. If BYOK affects whether custom braindumps hit Sam's API key vs. the visitor's, that's a real dependency. If it's just copy, it's not. → **Clarify or remove dependency.**
- **Animation style?** "Typewriter or fade" — cosmetic, but affects JS complexity. Typewriter implies character-by-character rendering; fade is a CSS transition between blocks. → **Pick one.**
- **How many demo braindumps, and who writes them?** Four categories listed but no content. Pre-computed responses require actual braindumps to exist before mock generation. → **This is on the critical path.**

## Dependencies & Sequencing
- Demo braindump content must be written → fed through real analysis → outputs cached as static JSON → landing page and app can reference them. This is a serial chain and the longest pole.
- Newspaper design tokens must be extracted from `web-ng/src/styles.css` into standalone CSS before landing page work begins — otherwise the landing page diverges visually.
- App must handle `?demo=true` route and sessionStorage reads before the landing page can redirect to it. App changes ship first or simultaneously.
- Conversion gate UX (what happens after the visitor sees results) must be designed before app integration — it determines whether the app needs a new modal, a banner, or a route guard.

## Explicitly Out of Scope
- **Pre-fired API calls from landing page** — requires cross-origin job tracking with no queue infrastructure. Let the app fire the call. Re-scope if latency data shows the extra seconds actually hurt conversion.
- **Shared component library between landing and app** — static HTML can't import Angular components. Duplicate the CSS, move on. Re-scope if a third surface (docs site, blog) needs the same tokens.
- **Auth flow design for the conversion gate** — the brain dump mentions "sign up to create your own" but the gate's UX is a separate spec. This epic covers landing → result. Gate is a handoff point, not a deliverable.
- **Demo braindump content creation** — writing four realistic braindumps and generating their cached responses is content work, not engineering. Track separately. Engineering just needs the JSON files to exist.

> **Cross-references:** Epic → `epic.md` § Landing Page CTA Funnel · Solution Architecture → `architecture.md` § Landing-to-App Data Flow · Implementation → landing page guide + app integration guide