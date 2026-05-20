# 🔍 Landing CTA App Handoff — Analysis

## The Problem
The landing page currently runs the full analyze flow inline — visitor never leaves the static page, never sees the real product. This wastes the highest-intent moment (someone just pasted their braindump and clicked Analyze) by showing a stripped-down rendering instead of onboarding them into the actual app. The fix: landing page becomes a dumb launcher — POST, get job_id, redirect.

## Hard Constraints
- Landing page and app are separate deployments (static site vs Angular on `app.specview.dev`)
- Backend already has `POST /api/public/analyze` — contract changes, not a net-new endpoint
- Projects live on the filesystem — anonymous projects use the same storage as authenticated ones
- No Redis, no Postgres — job state must live in-process or on disk
- Responses to Telegram under 4096 chars (irrelevant here, but shapes API response size)

## Open Questions
- **Cross-origin redirect**: Are landing page and app on the same domain (specview.dev / app.specview.dev) or fully separate? Determines whether the POST goes cross-origin or same-origin, and whether cookies/session could carry over. → *Same apex domain with subdomain* / *completely separate domains*
- **job_id = project_id or separate lookup?** The dump says "job_id maps to a real project_id." If they're the same value, the URL leaks the project_id (enumeration risk). If different, you need a mapping table. → *Same value, accept the risk* / *Short-lived opaque token that resolves to project_id*
- **Anonymous project TTL**: Unclaimed projects will accumulate on disk. What's the expiry? → *24h TTL cron cleanup* / *7d* / *never, manual cleanup*
- **Error path**: If `POST /api/public/analyze` fails (rate limit, bad input), the landing page has already committed to "fire and redirect." Does it show an error on the landing page, or redirect anyway and let the app show the error? → *Landing page shows error* / *Always redirect, app handles it*

## Dependencies & Sequencing
- **Backend first**: `POST /api/public/analyze` must create a real project and return a job_id that the app can poll — until this works, the redirect lands on nothing
- **App route before landing page change**: The Angular app needs a `/analyze?job=<id>` route that handles anonymous viewing before the landing page starts redirecting to it
- **Anonymous read-access gate**: The app's route guards currently require auth — a job_id-based bypass must exist before anything else is visible
- **Landing page change is last**: `analyze.js` swap from inline-render to POST+redirect is trivial but must ship after both backend and app are ready

## Explicitly Out of Scope
- **Sign-up / claim flow** — the dump mentions "visitor signs up and claims it" but that's a separate epic; this epic ends at "anonymous viewer can see their analysis." Re-scope when this ships and conversion data exists.
- **Rate limiting / abuse prevention on anonymous project creation** — real concern, but solve it with a simple IP-based throttle later, not in this epic. Re-scope if abuse appears in the first week.
- **Editing the landing page design/copy** — this is a plumbing change, not a redesign. Re-scope if conversion drops post-launch.
- **Authenticated user flow changes** — existing logged-in users are untouched. Don't entangle.