I have sufficient context from the exploration. Let me now write the Solution Architecture document.

# 🏗️ Solution Architecture: Auth Reliability & Credential Persistence

## Architecture Overview

The spec-doc API's AI capability depends entirely on a single authentication pathway to Claude. When that pathway breaks — currently every ~26 hours — every AI feature in the product returns a generic 502 and the only recovery is manual credential extraction via SSH. This architecture eliminates the daily auth failure cycle by converting the Claude CLI's credential lifecycle from ephemeral container state to persistent volume-backed state, and by fixing the error signal chain so that when auth does eventually degrade, the failure is diagnosable in seconds rather than hours.

The core insight, discovered through the May 12 incident, is that there are two distinct auth paths in the CLI provider and they are mutually exclusive. When `ANTHROPIC_CLI_KEY` is set, the provider adds `--bare` to every subprocess call, which tells the CLI to skip its own credential file entirely and use the env-provided token as a passthrough. This means the persistent volume approach only works if `ANTHROPIC_CLI_KEY` is removed — otherwise the CLI never touches the filesystem for auth and the volume is inert. The architecture therefore requires coordinated changes across three layers: environment variable removal (so `--bare` is no longer appended), volume persistence (so the CLI's self-managed session survives container restarts), and error signal recovery (so failures surface real diagnostics instead of empty strings).

The four components — CLI error capture, credential volume, environment cleanup with container login, and healthcheck wiring — form a dependency chain. Error capture and volume configuration are independent and can proceed in parallel. Environment cleanup depends on both being in place. Healthcheck wiring depends on the auth session being established. This ordering minimizes risk: the error capture improvement is valuable regardless of which auth strategy ultimately wins, and the volume mount is a no-op until the environment variables are cleaned up.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | All auth changes stay within `modules/runtime/chain/providers/cli.py` and the Docker infrastructure layer. No feature code is aware of how auth works — the adapter boundary remains the only file that knows which provider is active. The CLI provider's error handling improvement is purely internal to the provider module. |
| P2 — Thin HTTP Layer | The health endpoint at `/api/health/anthropic` already exists in `modules/observability/health.py` and performs a real `count_tokens` call. The architecture reuses this endpoint as the Docker healthcheck target — no new route logic, just infrastructure wiring. |
| P4 — No Speculative Abstractions | Option B (container login + persistent volume) solves the one concrete problem that exists now: daily token expiry on a pre-revenue product using Claude Max flat-rate billing. The architecture does not build a credential proxy sidecar, a token refresh cron, or a multi-provider failover system. Option A (API key) is documented as the future migration path but is not built speculatively. |
| P6 — Channel-Aware Context | The healthcheck endpoint serves both Docker's process-level health reporting and Coolify's dashboard. The same signal, consumed by two channels — no duplication of the health logic. |
| P7 — File Size & Structure | The CLI provider remains a single focused module. The entrypoint script gains one conditional guard. No new files are introduced — every change modifies an existing file within its current responsibility. |

## Component Design

### CLI Error Signal Recovery

**Purpose**: Surface the actual auth failure message so diagnosis takes seconds, not hours.

The CLI provider currently captures `stdout` and `stderr` separately via `subprocess.run(capture_output=True)`. On success, it returns `stdout`. On failure (non-zero exit code), it raises a `ProviderError` containing only the first 200 characters of `stderr`. The Claude CLI, however, writes auth errors like `Failed to authenticate. API Error: 401 Invalid authentication credentials` to **stdout**, not stderr. This means auth failures produce an error message with an empty string where the diagnostic should be — the most useful signal is silently discarded.

The fix is two-fold. First, when the CLI returns a non-zero exit code, the error message must include the first 200 characters of stdout alongside stderr. This is a mechanical change to the error construction in the provider's `generate` function. Second, the provider must scan the combined output for auth-specific signals — the string `401` or the word `authenticate` — and when detected, raise the `ProviderError` with HTTP status 401 instead of the default 502. This status code distinction flows through the adapter boundary unchanged and reaches the frontend, which can eventually use it to show "Authentication expired" instead of "Could not reach AI." The frontend differentiation is out of scope for this epic but the backend must provide the correct signal for it.

This component has no dependencies on the other three and should ship first. It improves diagnostics regardless of which auth strategy is in use.

### Credential Volume & Entrypoint Guard

**Purpose**: Make the CLI's self-managed credential file survive container lifecycle events.

Docker containers have ephemeral filesystems by default. When the Claude CLI refreshes an OAuth token, it writes the updated credentials to `/home/appuser/.claude/.credentials.json` inside the container. Without a volume, this file is destroyed on every `docker compose down` or container recreation. A named Docker volume mounted at `/home/appuser/.claude` decouples the credential file's lifecycle from the container's lifecycle. Named volumes persist across `down`/`up` cycles and are only removed by explicit `docker volume rm`.

The volume must be declared in both the production compose file and the local development override file. Both environments must behave identically — the local testing procedure validates the exact same persistence guarantees that production relies on.

The entrypoint script currently writes `CLAUDE_CREDENTIALS_JSON` to the credentials file path unconditionally on every boot. With the persistent volume, this behavior becomes destructive: it would overwrite CLI-refreshed credentials with the original stale seed on every restart. The entrypoint must be modified to check whether the credentials file already exists before writing. If the file is present (meaning the CLI has an active session on the volume), the entrypoint skips the write. If the file is absent (first boot, or volume was deliberately deleted), the entrypoint seeds from the environment variable as a bootstrap mechanism.

This creates a clean escape hatch: to force a credential re-seed, delete the named volume and restart. The entrypoint detects the missing file and re-seeds, after which a fresh `claude login` establishes a new session.

### Environment Cleanup & Container Auth Session

**Purpose**: Switch the CLI from passthrough token mode to self-managed session mode.

This is the most consequential change and depends on both prior components being in place. The current production auth flow sets `ANTHROPIC_CLI_KEY` in the environment, which the CLI provider reads at module import time into a module-level `_CLI_KEY` variable. When `_CLI_KEY` is truthy, two things happen: the `--bare` flag is appended to every CLI subprocess call, and a copy of `os.environ` with `ANTHROPIC_API_KEY` set to the CLI key value is passed as the subprocess environment. The `--bare` flag tells the Claude CLI to skip all credential file reads and use the environment-provided token directly — no refresh, no rotation, no filesystem interaction.

Removing `ANTHROPIC_CLI_KEY` from the environment causes `_CLI_KEY` to be `None`, which means `--bare` is never appended and the subprocess environment is not overridden. The CLI then falls back to its default behavior: read credentials from `~/.claude/.credentials.json`, use the refresh token to obtain fresh access tokens, and write rotated credentials back to the file. This is exactly the behavior the persistent volume is designed to preserve.

`CLAUDE_CREDENTIALS_JSON` must also be removed from the environment. With the seed-only-once entrypoint guard, this variable is only consumed on first boot when no credentials file exists. In practice, the preferred bootstrap path is `claude login` inside the container rather than env-var seeding, so the variable becomes a backup mechanism rather than the primary auth path.

The container login itself is a one-time manual step. Running `claude login` interactively inside the container (via `docker compose exec -it`) initiates an OAuth flow that creates a session with a long-lived refresh token. The CLI manages token rotation from that point forward. If the container environment lacks a browser (likely on the VPS), the CLI prints a URL for the operator to open externally, complete the OAuth flow, and paste the resulting code back into the terminal.

The adapter module (`adapter.py`) requires no changes. Its provider resolution logic already handles the absence of `ANTHROPIC_CLI_KEY` correctly — when neither `ANTHROPIC_API_KEY` nor `ANTHROPIC_CLI_KEY` is set and `CHAIN_PROVIDER` is `cli`, it falls through to the CLI provider, which runs without `--bare` and uses its own credential file. The adapter boundary is clean.

### Docker Healthcheck & Deployment Documentation

**Purpose**: Make auth failures visible in infrastructure tooling and document the operational procedures.

The existing Docker healthcheck (if any) checks process liveness — whether gunicorn is responding. This passes even when auth is completely broken, because the Flask process is healthy; it just can't reach Claude. The `/api/health/anthropic` endpoint in `modules/observability/health.py` already performs a real `count_tokens` call against the Anthropic API with a 5-second timeout and returns `{"status": "ok"}` or `{"status": "degraded"}` with the error message. Wiring this as the Docker healthcheck target means `docker ps` and Coolify's dashboard reflect actual auth status, not just process status.

The healthcheck interval of 60 seconds with 3 retries and a 120-second start period gives the container time to initialize and avoids false positives from transient network issues. A container marked unhealthy after three consecutive failures is a clear signal to the operator. Importantly, auto-restart on unhealthy would not help here — if credentials are invalid, restarting just re-runs the same broken auth. The healthcheck is for visibility, not remediation.

Deployment documentation must capture two distinct procedures: the initial setup (volume creation, environment cleanup, container login) and the recovery procedure (volume deletion, optional re-seed, re-login). Both must be executable by a solo operator via SSH without prior context.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Auth mechanism | Claude CLI self-managed OAuth session | Preserves Claude Max flat-rate billing. CLI handles token refresh internally — no custom refresh logic needed. |
| Credential persistence | Named Docker volume at `/home/appuser/.claude` | Survives `docker compose down`/`up` cycles. No host-path coupling. Deletable for clean recovery. |
| Healthcheck target | `/api/health/anthropic` (existing endpoint) | Already performs a real `count_tokens` API call. No new code — just infrastructure wiring. |
| Error detection | String matching on CLI stdout for `401`/`authenticate` | Pragmatic signal extraction. The CLI's error output format is not contractual, but auth keywords are stable enough for detection. |
| Entrypoint guard | File-existence check in shell script | Simplest possible conditional. No version tracking, no timestamp comparison — just "does the file exist." |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Option B (container login + volume) over Option A (API key) | Claude Max flat-rate billing is the only financially viable path pre-revenue. Per-token API billing at Opus-class generation volume is prohibitively expensive. | Refresh tokens eventually expire (weeks to months), requiring manual re-login. The failure window is extended, not eliminated. Accepted because the alternative costs more than the product earns. |
| Remove `ANTHROPIC_CLI_KEY` entirely rather than making it optional | When `_CLI_KEY` is truthy, `--bare` is appended unconditionally. There is no way to have the env var set and also have the CLI use its credential file. The two modes are mutually exclusive. | Loses the ability to inject a token from outside the container without interactive login. Mitigated by the entrypoint seed-only-once guard as a bootstrap fallback. |
| Seed-only-once entrypoint rather than removing the seeding logic entirely | Provides a bootstrap path for first-time container setup and a recovery mechanism after volume deletion. The env-var seeding becomes a safety net rather than the primary path. | Adds a conditional to the entrypoint that must be understood by future readers. Simpler than the alternative of requiring interactive login on every fresh volume. |
| Auth keyword detection via string matching rather than structured error parsing | The Claude CLI does not guarantee a stable error output format. Matching on `401` and `authenticate` is robust enough for the detection use case. | If the CLI changes its error wording, detection may break. The fallback is a generic 502 — no worse than the current behavior. |
| Healthcheck for visibility only, not auto-remediation | Auto-restart on auth failure creates a restart loop with no recovery path. The operator must intervene (re-login), so the healthcheck's job is to surface the problem, not fix it. | Auth failures are visible but not automatically resolved. Accepted because automated recovery would require a credential refresh mechanism that does not exist in this architecture. |
| Named volume rather than host-path bind mount | Named volumes are portable across environments (local dev, VPS, Coolify). Host-path mounts couple the container to a specific filesystem location and create permission issues with the `appuser` UID. | Credentials are not directly browsable on the host filesystem. Inspect via `docker compose exec` instead. Accepted because direct file access is a debugging convenience, not an operational requirement. |
| Loss of `--agent chain-agent` routing accepted | With `ANTHROPIC_CLI_KEY` removed and `--bare` no longer appended, the CLI runs in standard mode. Agent routing via `--agent` is still available in standard CLI mode when no system prompt is provided — the `_build_cmd` logic in `cli.py` already handles this. No capability is actually lost. | None — this was initially flagged as a risk but the code path confirms agent routing works without `--bare`. |

## Risk Assessment

**Refresh token expiry is the residual risk.** The Claude CLI's OAuth refresh tokens have a TTL measured in weeks to months, not hours. This converts a daily manual intervention into a quarterly one. If refresh token reliability proves worse than expected, the migration to Option A (API key) becomes the next architectural decision — the adapter already supports it via `CHAIN_PROVIDER=claude` with `ANTHROPIC_API_KEY`.

**The `claude login` flow inside a container is unvalidated.** The interactive OAuth flow may require browser access that is unavailable in a headless Docker environment. The expected workaround is `--no-browser` or URL-copy mode, where the CLI prints a URL, the operator opens it externally, and pastes the authorization code back. This must be validated locally before the VPS deployment.

**The healthcheck endpoint uses the Anthropic SDK lazily.** The `/api/health/anthropic` endpoint imports and instantiates the Anthropic client on first call. When `ANTHROPIC_API_KEY` is not set in the environment (which is the case under Option B — the CLI manages its own auth), the endpoint returns `{"status": "skipped"}`. This means the healthcheck may not actually validate CLI auth. The healthcheck implementation may need adjustment to perform a lightweight CLI call instead of an SDK call when the active provider is `cli`. This is flagged as a discovery item during local testing.

## Migration Path to Option A

When spec-doc reaches its first paying customer or the refresh token proves unreliable, the migration to API key auth is a configuration change, not an architecture change. Set `ANTHROPIC_API_KEY` in the environment, optionally set `CHAIN_PROVIDER=claude` (the adapter auto-resolves when the API key is present), and remove the credential volume. The adapter boundary ensures zero code changes in feature modules. The per-token cost becomes trackable per user, which aligns with SaaS billing. The healthcheck endpoint already works with the SDK provider. This is a 15-minute operational change, not a development task.

## Related Documents

- [Analysis](./analysis.md) — Root cause investigation, incident log, corrected mental model of the auth flow, and the critical discovery that `--bare` mode bypasses credential files entirely
- [Epic](./epic.md) — Scope boundaries, task breakdown, success criteria, and the explicit exclusion of frontend error differentiation and API key migration
- [Timeline](./timeline.md) — Task sequencing, dependency chain, and completion tracking