# Auth Reliability & Credential Persistence

## The Problem

Claude CLI OAuth credentials expire regularly, causing the spec generation pipeline to break with 502 errors. Currently requires manual intervention — extracting credentials from macOS keychain and restarting the container. On the VPS (Coolify), this means SSH-ing in or updating the Coolify UI. This is the #1 reliability issue blocking production use.

---

## Root Cause Analysis

The current flow has a fundamental flaw in how credentials are persisted:

1. `entrypoint.sh` writes `CLAUDE_CREDENTIALS_JSON` env var → `/home/appuser/.claude/.credentials.json` at container startup
2. Claude CLI auto-refreshes the OAuth token during use, writing updated credentials to that same file inside the container
3. But `~/.claude/` is NOT a mounted volume — refreshed credentials live only in the container's ephemeral filesystem
4. On container restart (deploy, crash, healthcheck failure), Docker re-runs the entrypoint with the ORIGINAL stale `CLAUDE_CREDENTIALS_JSON` from the env var
5. The refresh token from the original JSON may have been rotated by the CLI, so the old env var value is now completely dead
6. Result: every container restart risks breaking auth until someone manually re-extracts credentials

### Why it seems to work "for a while"

The OAuth access token has a short TTL (~1 hour). The refresh token is longer-lived. When the CLI refreshes, it gets a new access token AND sometimes a new refresh token. If the container doesn't restart during this window, everything's fine. But the moment it restarts, we're back to the stale seed credentials.

---

## Solution: Persistent Credential Volume

### Task 1 — Add a named Docker volume for `~/.claude/`

Add to `docker-compose.yml`:
```yaml
volumes:
  claude-credentials:

services:
  api:
    volumes:
      - claude-credentials:/home/appuser/.claude
```

And in `docker-compose.override.yml` for local dev:
```yaml
volumes:
  claude-credentials:

services:
  api:
    volumes:
      - claude-credentials:/home/appuser/.claude
```

This means the CLI's auto-refreshed credentials survive container restarts.

### Task 2 — Update entrypoint.sh to seed-only-once

Current entrypoint always overwrites. Change to only seed if the credentials file doesn't already exist:

```sh
if [ -n "$CLAUDE_CREDENTIALS_JSON" ] && [ ! -f /home/appuser/.claude/.credentials.json ]; then
    mkdir -p /home/appuser/.claude
    printf '%s' "$CLAUDE_CREDENTIALS_JSON" > /home/appuser/.claude/.credentials.json
fi
```

This way:
- First boot: env var seeds the credentials file
- Subsequent boots: CLI's auto-refreshed credentials are preserved
- Force re-seed: delete the volume (`docker volume rm specview_claude-credentials`) then restart

### Task 3 — Login to Claude directly on the VPS

SSH into the VPS and run:
```bash
docker compose exec api claude login
```

This gives the container its own persistent Claude session, independent of the Mac keychain. Combined with the persistent volume, the session survives restarts.

Alternative: `claude auth login` inside the container if the interactive login flow is available.

### Task 4 — Health check with credential validation

The existing `/api/health/anthropic` endpoint validates credentials via `count_tokens`. Wire this into the Docker healthcheck:

```yaml
healthcheck:
  test: ["CMD", "curl", "-sf", "http://127.0.0.1:3101/api/health/anthropic"]
  interval: 60s
  timeout: 10s
  retries: 3
  start_period: 120s
```

This surfaces auth failures in `docker ps` and Coolify's health dashboard, but note: auto-restart on auth failure won't help if the volume has stale credentials. The healthcheck is for visibility, not auto-fix.

### Task 5 — Credential refresh alerting

Add a simple alert mechanism when credentials are about to expire or have expired:
- Log a WARNING when the CLI returns a 401 or auth-related error
- Optionally: expose a `/api/health/anthropic` status in the app's status bar so the admin sees it immediately
- Future: webhook notification (Slack/email) on auth degradation

### Task 6 — Long-term: API key for production SaaS

For SaaS launch, switch production to `CHAIN_PROVIDER=claude` with an `ANTHROPIC_API_KEY`:
- API keys don't expire (until manually rotated)
- No OAuth refresh dance
- Pay-per-token pricing is better for multi-tenant SaaS (track cost per user)
- CLI provider is great for dev/self-hosted; SDK provider is right for production SaaS

The adapter already supports this — just set `ANTHROPIC_API_KEY` and the provider auto-resolves to SDK.

---

## Testing Plan

All changes must be validated locally with `docker compose` before touching the VPS:

1. **Test credential persistence**: Start container, make a generation call, restart container, verify credentials file still exists and generation still works
2. **Test seed-only-once**: Set `CLAUDE_CREDENTIALS_JSON`, start container, modify credentials file inside container, restart, verify the modified file is preserved (not overwritten)
3. **Test force re-seed**: Delete the volume, restart with `CLAUDE_CREDENTIALS_JSON` set, verify new credentials are written
4. **Test healthcheck**: Stop Claude auth (invalid credentials), verify healthcheck reports degraded
5. **Test VPS login**: SSH into VPS, `docker compose exec api claude login`, verify generation works

---

## Files to Change

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `claude-credentials` named volume, mount to api service |
| `docker-compose.override.yml` | Same volume mount for local dev |
| `api/entrypoint.sh` | Seed-only-once logic (check if file exists before writing) |
| `api/modules/runtime/chain/providers/cli.py` | Better error messages for auth failures (detect 401 in stderr) |
| `DEPLOY.md` | Update docs for VPS login flow and volume persistence |

---

## CORRECTION — Deployment Uses Env Var, Not Credentials File

### What actually happens in production

The original analysis above assumed the `.credentials.json` file path is what breaks. **That's wrong.** In deployment (Docker / Coolify), the CLI provider uses a completely different auth path:

```
Coolify env var: ANTHROPIC_CLI_KEY
  → Python: os.environ.get("ANTHROPIC_CLI_KEY") at module import
    → _build_env() copies it to ANTHROPIC_API_KEY in subprocess env
      → claude --bare -p ... (uses ANTHROPIC_API_KEY directly, skips keychain + credentials file)
```

The `--bare` flag means the CLI **never reads `.credentials.json`**. The `entrypoint.sh` / `CLAUDE_CREDENTIALS_JSON` mechanism is only relevant if someone runs `claude` interactively inside the container (e.g. `claude login`). It has nothing to do with the spec generation pipeline.

### Why tokens expire

`ANTHROPIC_CLI_KEY` holds an **OAuth access token** from Claude.ai (Claude Max subscription). These tokens have a short TTL (~1 hour). The CLI in `--bare` mode passes the token straight through — there's no refresh mechanism. Once the access token expires, every chain call gets a 401 and the API returns 502.

The persistent volume fix described above would not help, because `--bare` mode never touches the filesystem for auth.

### Revised solutions (in order of preference)

**Option A — Anthropic API key (recommended for SaaS)**

Switch production from CLI provider to SDK provider. Use a proper Anthropic API key that never expires:

```yaml
# docker-compose.yml / Coolify env
CHAIN_PROVIDER: claude
ANTHROPIC_API_KEY: sk-ant-api03-...
```

The adapter already supports this (`adapter.py:26-46`). When `ANTHROPIC_API_KEY` is set, it auto-resolves to the SDK provider (`providers/claude.py`). No OAuth, no refresh, no expiry. Pay-per-token.

Pros:
- Zero maintenance — API keys don't expire until manually revoked
- Pay-per-token is right for multi-tenant SaaS (track cost per user)
- SDK provider returns token counts (tokens_in/tokens_out) for usage tracking
- No dependency on Claude Max subscription

Cons:
- Costs money per token (vs Claude Max flat rate)
- Need to set up billing alerts to avoid surprise bills
- Loses access to Claude Code agent routing (`--agent chain-agent`)

**Option B — Login inside container + persistent volume**

SSH into VPS and login interactively:
```bash
docker compose exec api claude login
```

This creates a session in `/home/appuser/.claude/` with a refresh token. The CLI (when run without `--bare`) auto-refreshes.

Requires:
1. Add a named volume for `~/.claude/` so the session survives restarts
2. **Remove `ANTHROPIC_CLI_KEY` from env** so `_CLI_KEY` is empty and `--bare` is NOT added
3. CLI then uses its own credential file and handles refresh internally

```yaml
# docker-compose.yml
volumes:
  claude-credentials:

services:
  api:
    volumes:
      - claude-credentials:/home/appuser/.claude
    environment:
      CHAIN_PROVIDER: cli
      # DO NOT set ANTHROPIC_CLI_KEY — let CLI use its own session
```

Pros:
- Uses Claude Max flat rate (no per-token cost)
- CLI handles token refresh automatically
- Keeps agent routing (`--agent chain-agent`)

Cons:
- One-time manual login on the VPS
- If the refresh token eventually expires (rare), need to re-login
- Persistent volume adds operational complexity

**Option C — External token refresh cron (fragile, not recommended)**

A cron on the VPS that periodically calls the OAuth refresh endpoint and updates the Coolify env var. This is complex, fragile, and the refresh endpoint is not publicly documented. Not recommended.

### What to do now

1. **Immediate (local testing)**: Try Option B locally with docker compose — remove `ANTHROPIC_CLI_KEY`, add the volume, run `docker compose exec api claude login`, test that generation works and survives restarts
2. **Short-term (VPS)**: Apply Option B to Coolify — login once, persistent volume
3. **SaaS launch**: Switch to Option A (API key) — proper pay-per-token, no OAuth dependency

### Revised files to change

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `claude-credentials` named volume |
| `docker-compose.override.yml` | Mount volume, remove `ANTHROPIC_CLI_KEY` for Option B |
| `api/modules/runtime/chain/providers/cli.py` | Detect 401/auth errors in stderr, surface clear message |
| `api/modules/runtime/chain/adapter.py` | No change needed — SDK provider already works |
| `DEPLOY.md` | Document Option A (API key) and Option B (container login) |
| Coolify env vars | Either set `ANTHROPIC_API_KEY` (Option A) or remove `ANTHROPIC_CLI_KEY` (Option B) |

---

## Incident Log — 2026-05-12: "Could not reach AI" in local Docker

### Symptoms
- All AI operations (brainstorm, text ops, bootstrap) return the generic frontend error: *"Could not reach AI — check connection."*
- API logs show: `cli non_zero_exit model=claude-opus-4-6 code=1 stderr=` — exit code 1 but **empty stderr**
- The frontend `aiError` signal triggers the catch-all error message (`app.component.ts:641-642`)

### Root cause
The OAuth access token inside the container's `.credentials.json` expired:
```
Container token expiresAt: 1778509749582 → 2026-05-11 16:29 (yesterday)
```
The `CLAUDE_CREDENTIALS_JSON` env var was set when the container was first created and never updated. The entrypoint writes this stale JSON to `/home/appuser/.claude/.credentials.json` on every restart, overwriting any CLI auto-refresh that may have happened.

The CLI returned `401 Invalid authentication credentials` on stdout but nothing on stderr, so the Python error log showed an empty stderr — making diagnosis harder.

### Fix applied
```bash
# 1. Extract fresh token from Mac keychain
CLAUDE_CREDENTIALS_JSON="$(security find-generic-password -s 'Claude Code-credentials' -w)" \
  docker compose up -d api

# 2. Verified
docker compose exec api claude -p "say hello" --output-format text
# → "Hello"
```

Fresh token expires: `1778604550488 → 2026-05-12 18:49` (valid ~10 hours).

### Why stderr was empty
The Claude CLI prints auth errors to **stdout**, not stderr. The CLI provider (`cli.py:68`) only logs `result.stderr[:200]`, so the actual 401 message was silently discarded. The `ProviderError` message was: `claude CLI exited with code 1: ` (trailing empty string).

### Observations for the fix
1. **`cli.py` should capture stdout on failure too** — when `returncode != 0`, include `result.stdout[:200]` in the error message alongside stderr. This would have shown `Failed to authenticate. API Error: 401 Invalid authentication credentials` immediately.
2. **The frontend error is too generic** — `"Could not reach AI — check connection"` doesn't distinguish between auth failure (401), rate limit (429), server error (500), or network down. The backend already returns different status codes (502 for CLI failure, 503 for rate limit, 504 for timeout) but the frontend doesn't use them.
3. **No alerting** — there's no way to know the API is broken until a user tries to generate and sees the error. The healthcheck (`/api/health`) passes because it checks the Flask process, not Claude auth. The `/api/health/anthropic` endpoint exists but isn't wired as the Docker healthcheck.
4. **This will happen again tomorrow** — the token TTL is ~26 hours. Without one of the P0 fixes (persistent volume + container login, or API key), this is a daily manual task.

### Quick wins to implement from this incident
| # | Fix | Effort |
|---|-----|--------|
| 1 | `cli.py`: include stdout in error when returncode != 0 | 5 min |
| 2 | `cli.py`: detect "401" or "authenticate" in output, raise `ProviderError(msg, 401)` | 10 min |
| 3 | Frontend: show backend error message instead of generic string when available | 30 min |
| 4 | Docker healthcheck: switch to `/api/health/anthropic` | 5 min |
| 5 | `scripts/credentials-refresh.sh`: also restart the api container | 5 min |

---

## AI Analysis — 2026-05-12

### 1. Key Themes

**Error signal attenuation is the real villain.** The auth expiry is annoying but diagnosable — what made this a multi-hour incident is that the error signal degraded at every boundary. CLI prints to stdout not stderr. Python logs empty stderr. Backend returns generic 502. Frontend shows "check connection." By the time a human sees the problem, every useful diagnostic detail has been stripped. This is a systemic observability failure, not just a missing log line.

**The mental model was wrong before it was right.** The document's most revealing structural feature is the CORRECTION section. The entire first half designs a solution (persistent volume + seed-only-once entrypoint) for a problem that doesn't exist in production — because `--bare` mode bypasses the credentials file entirely. This is a textbook case of fixing the system you think you have rather than the system you actually have. The correction is honest and valuable, but it means the team's internal model of the auth flow was wrong until an incident forced a re-examination.

**Container ephemerality and OAuth are fundamentally incompatible.** Docker assumes processes are stateless and restartable. OAuth assumes a long-lived agent that can rotate its own refresh tokens. These two assumptions collide silently — everything works until a restart lands in the wrong window. This isn't a bug to fix; it's an architectural tension to resolve by picking a side (stateless API key or stateful persistent session).

**The CLI provider is a development convenience masquerading as production infrastructure.** Using Claude CLI in `--bare` mode with a manually-extracted OAuth token from a macOS keychain is a perfectly reasonable dev setup. It becomes a ticking time bomb the moment it's the production auth path for a SaaS API. The document already knows this (Option A is the recommended long-term fix), but the urgency framing suggests the team has been living with this tension for a while.

**The 26-hour token TTL creates a deceptive rhythm.** It works all day, breaks overnight, gets fixed in the morning. This is exactly the failure pattern that teams tolerate for weeks because it's "manageable" — until it happens during a demo, or on a weekend, or when the person who knows the keychain extraction trick is unavailable.

### 2. Hidden Connections

**The CORRECTION section and the empty-stderr bug are the same epistemological failure.** In both cases, the team was reasoning about a system they couldn't fully observe. The credentials file assumption was wrong because nobody traced the actual auth path in production. The empty stderr was misleading because nobody checked where the CLI actually writes errors. Both problems stem from insufficient observability of the actual runtime behavior — and both were only discovered through incidents, not instrumentation.

**The healthcheck gap and the frontend error generality are two ends of the same pipe.** The Docker healthcheck doesn't test auth. The frontend doesn't surface auth-specific errors. Together, they create a blind spot where auth can be completely broken and the only signal is a user seeing a generic error. Fix either end and the other becomes less critical — but both being broken simultaneously means auth failures are invisible to both operators and users.

**Option B (container login + volume) recreates the Mac keychain problem at a different layer.** Right now, credentials come from a Mac keychain and break when the token expires. Option B moves credentials to a Docker volume and they'll break when the refresh token expires. The failure mode is the same — a long-lived credential that eventually rots — just with a longer TTL. Option A (API key) is the only solution that actually eliminates the credential lifecycle problem rather than extending it.

**The cost concern about API keys is a proxy for an unresolved business model question.** The document notes that Claude Max flat rate is cheaper than pay-per-token for the current usage pattern. But if this is a SaaS product, the cost structure needs to be per-user anyway. The reluctance to switch to API keys isn't really about cost — it's about not yet having the billing infrastructure to make per-token costs sustainable. The auth fix and the billing system are quietly coupled.

**"Quick wins" #1 and #2 (better error capture in cli.py) would have prevented the CORRECTION section from being necessary.** If the error message had said `401 Invalid authentication credentials` from the start, the team would have immediately known the problem was token expiry, not credential file persistence. Better error messages don't just help debugging — they prevent entire categories of wrong-direction investigation.

### 3. Open Questions

**When does Option A (API key) actually get deployed, and what's blocking it?**
- Option 1: Deploy Option A now, skip Option B entirely. Accept the per-token cost as the price of reliability.
- Option 2: Deploy Option B now as a bridge, migrate to Option A at SaaS launch.
- Option 3: Deploy Option B now and defer Option A indefinitely (Claude Max stays cheaper for single-tenant use).
- Recommended: Option 1 — deploy the API key now. Option B is operational complexity that only buys you time. Every day spent on the bridge solution is a day you could have been running reliably on the permanent solution. The per-token cost for a pre-launch product is negligible compared to the engineering time spent fighting auth failures.

**Is the `--agent chain-agent` routing that Option A loses actually load-bearing?**
- Option 1: It's critical — the agent routing does something the SDK provider can't replicate (tool use, multi-step reasoning, etc.).
- Option 2: It's a nice-to-have that marginally improves output quality but isn't essential.
- Option 3: It's vestigial — the spec generation pipeline doesn't use any agent-specific features.
- Recommended: Option 3 is most likely, but verify by running the same prompts through both providers and diff the outputs. If agent routing matters, it should be measurably better — and if you can't measure the difference, it doesn't matter.

**What's the actual blast radius of an auth failure — just spec generation, or does it break other features too?**
- Option 1: Only spec generation uses the Claude provider — other features (brainstorm, text ops) use a different path.
- Option 2: All AI features go through the same chain adapter and all break simultaneously.
- Option 3: Some features have fallback providers and degrade gracefully; others hard-fail.
- Recommended: Option 2 seems likely from the incident log ("All AI operations return the generic frontend error"). Map every feature to its provider dependency and make this explicit — you need to know your actual failure domain before you can design alerting that covers it.

**Why is the frontend error handling a catch-all instead of using the status codes the backend already returns?**
- Option 1: Historical — the frontend was built before the backend had differentiated error codes.
- Option 2: Intentional — someone decided users shouldn't see technical error details.
- Option 3: The Angular error interceptor catches the HTTP error before the component-level handler can differentiate.
- Recommended: Option 1 or 3 — either way, fix it. The backend already returns 401/429/502/503/504. The frontend should show "Authentication expired — contact admin" for 401, "Rate limited — try again in a moment" for 429, etc. This is 30 minutes of work that permanently improves every future incident.

**Is there a monitoring/alerting stack already in place, or would credential alerting be the first alerting of any kind?**
- Option 1: Coolify has built-in alerting that just needs to be configured for the healthcheck.
- Option 2: No alerting exists — need to set up from scratch (Uptime Kuma, Healthchecks.io, etc.).
- Option 3: There's a Slack/Discord webhook already in use for deploys that could be extended.
- Recommended: Option 1 if available — Coolify supports healthcheck-based notifications natively. Check Coolify's notification settings before building anything custom.

**Has anyone validated that `claude login` actually works inside a Docker container with no TTY forwarding?**
- Option 1: It works with `docker compose exec -it` which allocates a pseudo-TTY.
- Option 2: It requires a browser-based OAuth flow that won't work headless — needs `--no-browser` flag and manual URL copy.
- Option 3: It doesn't work at all in a container and Option B is a dead end.
- Recommended: Option 2 is most likely. Test this locally before planning a VPS deployment around it. If the login flow requires browser interaction, document the exact steps (including the URL-copy workaround) so any team member can do it.

### 4. Ideas to Explore

**Ship Quick Win #1 (stdout in error messages) today, before doing anything else.** It's 5 minutes of work and it transforms every future auth debugging session from "why is stderr empty?" to "oh, 401, token expired." This single change would have saved hours on this incident and will save hours on the next one. Do it now.

**Build a `/api/status` dashboard page that shows provider health in real-time.** Not just a JSON healthcheck endpoint — an actual HTML page that shows: which provider is active, when the last successful call was, what the last error was, and what the token expiry time is (if knowable). Make it the browser homepage for the team. This turns auth failures from "discovered when a user complains" to "visible at a glance."

**Add a startup self-test to the API.** On boot, before accepting traffic, make one real Claude call (a minimal `count_tokens` or "say ok" call). If it fails, log a CRITICAL error and exit with a non-zero code. This turns auth failures into deploy failures — which are much more visible than runtime failures. The container won't start healthy with broken auth.

**Instrument the chain adapter with structured logging that includes auth metadata.** Every chain call should log: provider used, auth method (API key vs CLI token vs OAuth), response status, latency, and token counts. Pipe this to whatever logging stack exists. Right now the logs say `cli non_zero_exit code=1 stderr=` — that's not enough to debug anything. Structured logs make patterns visible (e.g., "401s started at 4:29pm" maps directly to token expiry).

**Write a `make auth-check` target that validates the current auth setup end-to-end.** It should: check which provider is configured, verify the relevant credential exists and is not expired, make a test call, and print a clear pass/fail. Run this in CI, run it before deploys, run it manually when things seem wrong. One command that answers "is auth working right now?"

**Consider a credential proxy pattern for the transition period.** If you're not ready to switch to API keys yet, run a tiny sidecar container that holds the OAuth session, auto-refreshes tokens, and exposes a local endpoint that returns a fresh access token on demand. The main API container calls the sidecar instead of managing credentials itself. This decouples the auth lifecycle from the application lifecycle — and when you eventually switch to API keys, you just remove the sidecar. Over-engineered for a solo project, but useful if multiple services need Claude auth.

**Rewrite the document with the correct mental model.** The current document is a forensic record of how understanding evolved, which is valuable for a postmortem — but as an implementation plan, having a wrong solution followed by a correction is confusing. Rewrite it as: here's how auth actually works, here's why it breaks, here are the options ranked. Keep the incident log as a separate document.

**Set a calendar reminder for before the current token expires (18:49 today).** If the API key switch isn't done by then, the 26-hour cycle will bite again. Don't let the fix be "I'll get to it before it expires" — that's exactly the pattern that created this problem.

---

## DECISION — 2026-05-12: Container Login + Persistent Volume (Option B)

**Chosen approach:** Log into Claude directly inside the container, persist the session with a named Docker volume. Reuse the Claude Max subscription — API keys are not financially viable.

**Why not API key (Option A):** Can't afford per-token billing. Claude Max flat rate is the only cost-viable path for the current stage. The analysis above recommending Option A assumed API key cost was negligible — it isn't when you're pre-revenue running Opus-class generation at volume.

**The implementation:**

1. **Add a named Docker volume** for `/home/appuser/.claude/` so the CLI's credentials file and auto-refreshed tokens survive container restarts.

2. **Remove `ANTHROPIC_CLI_KEY` from the environment.** This is critical. When `ANTHROPIC_CLI_KEY` is set, the Python module sets `_CLI_KEY`, which causes `--bare` to be added to every CLI call. `--bare` tells the CLI to skip its own credential file and use `ANTHROPIC_API_KEY` from the environment instead — bypassing the persistent session entirely. If you leave this env var set, the volume mount is pointless.

3. **Remove `CLAUDE_CREDENTIALS_JSON` from the environment.** The entrypoint.sh writes this to `.credentials.json` on every boot, overwriting whatever the CLI auto-refreshed. With the persistent volume approach, the credentials file is owned by the CLI's own session — the entrypoint seeding is no longer needed.

4. **SSH into the VPS (or local container) and run `claude login`.** This creates a session with a long-lived refresh token. The CLI handles token rotation internally from that point forward.

5. **Update `entrypoint.sh`** to only seed credentials if the file doesn't already exist (safety net for first boot, doesn't overwrite CLI-managed sessions).

**What this buys us:** The 26-hour manual refresh cycle becomes a much longer cycle (refresh tokens last weeks to months). The CLI handles access token rotation internally. Container restarts preserve the session via the volume.

**What this doesn't solve:** The fundamental tension between Docker ephemerality and OAuth statefulness remains. If the refresh token eventually expires, someone has to re-login manually. We've extended the failure window, not eliminated it. This is a known, accepted tradeoff — the alternative (API keys) is not affordable right now.

**Files to change:**

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `claude-credentials:` named volume, mount to `/home/appuser/.claude` on api service |
| `docker-compose.override.yml` | Same volume mount, remove `CLAUDE_CREDENTIALS_JSON` env var |
| `api/entrypoint.sh` | Seed-only-once: skip write if `.credentials.json` already exists |
| `api/modules/runtime/chain/providers/cli.py` | Include stdout in error messages (Quick Win #1 from incident) |
| `DEPLOY.md` | Document the `claude login` procedure for VPS |

**Constraint: all changes must be validated locally with `docker compose` before merging to master.**

Nothing ships to VPS until every step below passes on the local machine. The local override file (`docker-compose.override.yml`) already maps ports 8095/8096 and mounts the data directory — the test environment is identical to production minus the domain.

### Local testing procedure (must all pass before merge)

**Phase 1 — Apply code changes and rebuild**
```bash
# Branch already exists: feat/ux-overview-polish (or create a new one)
# Apply all file changes listed above, then:
docker compose build api
docker compose up -d api
```

**Phase 2 — Login inside the container**
```bash
# Allocate a TTY for the interactive login flow
docker compose exec -it api claude login

# If headless (no browser), the CLI will print a URL — copy it,
# open in your Mac browser, complete OAuth, paste the code back.
# Verify the session was created:
docker compose exec api ls -la /home/appuser/.claude/.credentials.json
```

**Phase 3 — Verify generation works**
```bash
# Direct CLI test
docker compose exec api claude -p "say hello in one word" --output-format text
# Expected: a one-word response, no auth errors

# API endpoint test (through nginx proxy)
curl -s -X POST http://localhost:8095/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"sam@specview.app","password":"salt"}' | python3 -m json.tool
# Grab the token from the response, then:
TOKEN="<paste token>"
curl -s http://localhost:8095/api/health/anthropic | python3 -m json.tool
# Expected: {"status": "ok"}
```

**Phase 4 — Verify credentials survive restart**
```bash
# Record the credentials file timestamp
docker compose exec api stat /home/appuser/.claude/.credentials.json

# Restart the container (this re-runs entrypoint.sh)
docker compose restart api

# Wait for healthy
docker compose ps  # should show (healthy)

# Verify the credentials file was NOT overwritten by entrypoint
docker compose exec api stat /home/appuser/.claude/.credentials.json
# Timestamp should be unchanged (seed-only-once logic preserved it)

# Verify generation still works after restart
docker compose exec api claude -p "say hello in one word" --output-format text
# Expected: works, no 401
```

**Phase 5 — Verify volume survives full teardown**
```bash
# Full down + up (not just restart — this destroys and recreates containers)
docker compose down
docker compose up -d

# The named volume should persist across down/up
docker compose exec api ls -la /home/appuser/.claude/.credentials.json
# File should still exist

docker compose exec api claude -p "say hello in one word" --output-format text
# Expected: still works
```

**Phase 6 — Verify the app end-to-end**
```bash
# Open http://localhost:8095 in browser
# Login with sam@specview.app / salt
# Open any project with a braindump
# Click Brainstorm or any AI op
# Expected: operation completes, no "Could not reach AI" error
```

**Phase 7 — Verify force re-seed (escape hatch)**
```bash
# If the persistent session ever goes bad, this is the recovery path:
docker volume rm specview_claude-credentials
CLAUDE_CREDENTIALS_JSON="$(security find-generic-password -s 'Claude Code-credentials' -w)" \
  docker compose up -d api
# Entrypoint seeds the credentials file (because it doesn't exist yet)
# Then re-login: docker compose exec -it api claude login
```

### Merge criteria

All seven phases must pass. Only then:
1. Create PR against master
2. CI must pass (pytest, structural tests)
3. Merge
4. Deploy to VPS via Coolify
5. SSH into VPS, run `docker compose exec -it api claude login` once
6. Verify with `/api/health/anthropic` on production domain
