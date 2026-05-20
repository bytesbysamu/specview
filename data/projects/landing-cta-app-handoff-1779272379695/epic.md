# 🎯 Epic: Landing CTA App Handoff

## Business Value

The landing page's Analyze CTA is the highest-intent moment in the entire funnel — a visitor has pasted their own braindump and clicked the button. Right now, that moment is wasted: the result renders inline on a static page, the visitor never touches the real product, and there is zero path from "impressed by the output" to "signed up and using it." The visitor leaves having seen a demo, not having used the tool.

Redirecting into the real app turns that moment into an onboarding event. The visitor sees their analysis inside the actual project view — the same UI authenticated users see — and immediately understands what the product *is*. A real project is created on the backend, so when the visitor decides to sign up, their work is already there waiting. This eliminates the dead-end experience and creates a natural conversion funnel: free analysis → real app context → sign-up to unlock the full spec suite.

This is the single highest-leverage change for spec-doc's growth loop. Every other acquisition effort (content, SEO, word-of-mouth) funnels through the landing page CTA. Moving from "demo on a static page" to "real product experience" changes the conversion surface from a screenshot to a test drive. The cost is low — the backend, the app, and the landing page all exist; this epic is plumbing, not a rebuild.

## Scope

### What This Epic Covers

- **Anonymous project creation** – `POST /api/public/analyze` creates a real filesystem project and runs analysis against it, returning a job_id the app can poll
- **App-side anonymous analyze route** – A new route in the Angular app that accepts a job_id, bypasses auth guards, polls for progress, and renders the analysis in the real project view
- **Landing page handoff** – Replace inline result rendering in `analyze.js` with a POST + redirect to the app
- **Anonymous project cleanup** – TTL-based expiry so unclaimed anonymous projects do not accumulate indefinitely on disk

### What This Epic Does NOT Cover

- ❌ **Sign-up and project claim flow** — The visitor can *view* their analysis; claiming it under an account is a separate epic. Revisit once this ships and conversion data exists.
- ❌ **Rate limiting / abuse prevention** — Anonymous project creation is unthrottled in this epic. Add IP-based throttle if abuse appears in the first week post-launch.
- ❌ **Landing page redesign** — This is a plumbing change to the CTA, not a copy or design update. Revisit if conversion drops.
- ❌ **Authenticated user flow changes** — Logged-in users are completely untouched. Do not entangle.
- ❌ **Cross-project anonymous session management** — One braindump = one anonymous project. No session continuity across multiple analyses.

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Backend: Anonymous Project Creation & Job Polling** — Modify `POST /api/public/analyze` to create a real filesystem project, persist the braindump, kick off async analysis, and return a job_id. Expose `GET /api/public/analyze/<job_id>` for polling with progressive results. | None | — | 2 days | High |
| 2 | **App: Anonymous Analyze Route with Auth Bypass** — Add `/analyze?job=<id>` route in the Angular app. Read job_id from query params, bypass auth route guards for this path, poll the backend status endpoint, and render the analysis progressively in the real project view UI. | 1 | — | 2 days | High |
| 3 | **Landing Page: POST + Redirect Handoff** — Replace the inline rendering logic in `analyze.js` with a POST to `/api/public/analyze`, extract the returned job_id, and redirect the browser to `app.specview.dev/analyze?job=<job_id>`. Remove all result-rendering DOM logic from the landing page. | 1, 2 | — | 0.5 days | High |
| 4 | **Anonymous Project TTL Cleanup** — Scheduled cleanup of anonymous projects that were never claimed. Filesystem sweep on a cron interval, deleting project directories past the configured TTL. | 1 | 2, 3 | 1 day | Low |

## Success Criteria

- ✅ Visitor pastes braindump on landing page, clicks CTA, and lands inside the real Angular app within 3 seconds — never sees results on the landing page itself
- ✅ The app renders the analysis progressively using the same project view UI that authenticated users see
- ✅ A real project exists on the filesystem after the anonymous analyze call — braindump persisted, analysis output written to the same project directory
- ✅ The job_id URL is the only credential required to view the anonymous analysis — no login prompt, no auth wall
- ✅ Anonymous projects without a claim are automatically cleaned up after their TTL expires
- ✅ Existing authenticated user flows are unaffected — no regressions in the logged-in analyze path

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design for anonymous project creation, auth bypass, and cross-origin handoff
- [Timeline](./timeline.md) – Status tracking