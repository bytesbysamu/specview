# Bugs & Issues — Remote Deployment Testing

Tracked during pre-launch testing (2026-05-15).

---

## Auth

- [ ] **Login doesn't redirect to overview** — after successful login, no navigation happens. `isLoggedIn` signal flips but route stays on `/login`. Login component needs `router.navigate(['/'])` on success.
- [ ] **Authenticated user sees login page** — visiting `/login` with a valid token should redirect to overview, not show the sign-in form.
- [ ] **No password reset flow** — locked out users have no recovery path.
- [ ] **No email verification on signup** — spam account risk.

## Rate Limiting

- [x] **Login rate limit too strict** — was 5 req/hour, changed to 15 req/15min locally. Needs deploy.

## Status Bar — Consolidate to One

- [ ] **Two status bars exist, should be one** — there's a status bar at the top (tracks generation) and another inside the expanded spec detail view (tracks brainstorm/text ops). Consolidate into a single status bar on the overview, not inside the detail view. It should handle everything: spec generation, text operations, brainstorming. Duplication does not make sense.
- [ ] **Status bar should be sticky below masthead** — the status bar should stick just below the masthead nav (Context | All | Active | Ready to Build | Specced | Braindumps), same behavior as the nav buttons. Stays fixed when scrolling.

## Deployment / Infra

- [ ] **Landing page 504 on Coolify** — explicit `specview` network caused dual-network Traefik routing. Fix merged (PR #56), needs Coolify redeploy.
- [x] **Project creation 404** — `git_store._repos_base()` missing env var fallback. Fixed (PR #56).
- [x] **Retry button no-op** — status bar retry just cleared error, now delegates to `onRetry()`. Fixed (PR #56).
- [ ] **Stripe in test mode** — needs live keys before launch.
- [ ] **`CHAIN_PROVIDER=cli` in prod** — should switch to `claude` SDK for token counting + cost tracking.
