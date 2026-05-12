# Implementation Guide: Auth Reliability & Credential Persistence

## Overview
This epic converts the spec-doc API's Claude authentication from a daily-expiring, manually-recovered OAuth token to a persistent, self-refreshing CLI session backed by a Docker volume. The work sequences in four tasks: first, fix the error signal chain so auth failures are diagnosable (Task 1) and configure the persistent credential volume (Task 2) — these two are independent and can proceed in parallel. Then remove the environment variables that force the CLI into passthrough mode and establish an interactive login session (Task 3). Finally, wire the existing health endpoint as the Docker healthcheck target and document the operational procedures (Task 4).

## Shared Pre-flight
- Confirm you can run `docker compose up -d` and `docker compose exec api bash` against the local dev environment
- Identify the two compose files in the repository: the production compose file and the local development override file
- Locate `modules/runtime/chain/providers/cli.py` and read the `generate` method, the `_CLI_KEY` module-level variable, and the `_build_cmd` helper
- Locate `modules/observability/health.py` and read the `/api/health/anthropic` endpoint handler
- Locate `entrypoint.sh` and read the block that writes `CLAUDE_CREDENTIALS_JSON` to disk
- Identify where `ANTHROPIC_CLI_KEY` and `CLAUDE_CREDENTIALS_JSON` are defined in environment configuration (compose files, `.env` files, or Coolify config)
- Verify that `CHAIN_PROVIDER` is set to `cli` in the target environment
- Back up any existing credentials or environment files before making changes

---

## Task 1: CLI Error Signal Recovery  [Effort: 0.5 days]

### What
The CLI provider currently discards stdout on failure, but the Claude CLI writes auth errors to stdout, not stderr. This task modifies the error construction to include stdout in failure messages and detects auth-specific keywords to raise a 401 instead of a generic 502, making auth failures diagnosable in seconds.

### Files
- **Modify**: `modules/runtime/chain/providers/cli.py` — Change the error-handling path in the `create_message` function to include stdout in the raised `ProviderError` message, and add auth-keyword detection to set the correct HTTP status code

### Steps
1. In `cli.py`, find the branch in `create_message` that handles a non-zero exit code from `subprocess.run`. The current `ProviderError` is constructed using only the first 200 characters of `result.stderr`.
2. Change the error message construction to concatenate the first 200 characters of `result.stdout` with the first 200 characters of `result.stderr`, separated by a clear label so the operator can distinguish the two streams.
3. After constructing the combined error string, scan it for auth-specific signals: the substring `401` or the case-insensitive word `authenticate`.
4. When an auth signal is detected, raise the `ProviderError` with HTTP status code 401. When no auth signal is detected, preserve the existing 502 behavior.
5. Run the existing test suite for the CLI provider to confirm no regressions in the success path or other error paths.

### Verify
- Simulate a CLI auth failure (e.g., corrupt the credentials file) and confirm the error message returned by the API includes the stdout content with the actual auth error text
- Confirm the HTTP response status is 401 when the error contains auth keywords
- Confirm the HTTP response status remains 502 for non-auth CLI failures (e.g., network timeout)
- Run `python -m pytest` for the CLI provider module and confirm all tests pass

---

## Task 2: Credential Volume & Entrypoint Guard  [Effort: 0.5 days]

### What
Container restarts destroy the CLI's refreshed credentials because the filesystem is ephemeral. This task adds a named Docker volume at `/home/appuser/.claude` so credentials survive container lifecycle events, and modifies the entrypoint to skip credential seeding when a credentials file already exists on the volume.

### Files
- **Modify**: `docker-compose.yml` (production) — Add a named volume declaration and mount it at `/home/appuser/.claude` on the api service
- **Modify**: `docker-compose.override.yml` (local dev) — Add the same named volume declaration and mount to ensure local testing matches production
- **Modify**: `entrypoint.sh` — Wrap the `CLAUDE_CREDENTIALS_JSON` write block in a file-existence check so it only seeds when `/home/appuser/.claude/.credentials.json` is absent

### Steps
1. In the production compose file, add a top-level `volumes` entry declaring a named volume (e.g., `claude-credentials`). Under the api service's `volumes` section, mount it at `/home/appuser/.claude`.
2. Repeat the identical volume declaration and mount in the local development compose override file.
3. In `entrypoint.sh`, find the line or block that writes the `CLAUDE_CREDENTIALS_JSON` environment variable contents to `/home/appuser/.claude/.credentials.json`.
4. Wrap that block in a shell conditional that checks whether `/home/appuser/.claude/.credentials.json` already exists. If the file exists, skip the write and log a message indicating that existing credentials were preserved. If the file does not exist, execute the original write logic.
5. Test locally by running `docker compose up -d`, verifying the volume is created with `docker volume ls`, then running `docker compose down && docker compose up -d` and confirming the volume persists.

### Verify
- `docker volume ls` shows the named credential volume after `docker compose up -d`
- `docker compose down && docker compose up -d` does not remove the volume — confirm with `docker volume ls`
- Place a test file inside the container at `/home/appuser/.claude/.credentials.json`, restart the container, and confirm the file content is unchanged (entrypoint did not overwrite)
- Remove the volume with `docker volume rm`, restart, and confirm the entrypoint re-seeds the credentials file from the environment variable

---

## Task 3: Environment Cleanup & Container Auth Session  [Effort: 1 day]

### What
The `ANTHROPIC_CLI_KEY` environment variable forces the CLI into `--bare` passthrough mode, which bypasses credential file reads entirely and makes the persistent volume inert. This task removes both `ANTHROPIC_CLI_KEY` and `CLAUDE_CREDENTIALS_JSON` from the environment, then establishes a persistent CLI session via interactive `claude login` inside the container.

### Files
- **Modify**: `docker-compose.yml` — Remove `ANTHROPIC_CLI_KEY` and `CLAUDE_CREDENTIALS_JSON` from the api service's environment section
- **Modify**: `docker-compose.override.yml` — Remove the same two variables from the local dev environment section
- **Modify**: `.env` or equivalent environment file — Remove both variables if defined there
- **Modify**: `entrypoint.sh` — Remove or guard any remaining references to `ANTHROPIC_CLI_KEY` that would conflict with the new auth mode

### Steps
1. Search across all compose files, `.env` files, and any Coolify-specific config for references to `ANTHROPIC_CLI_KEY` and `CLAUDE_CREDENTIALS_JSON`. Remove every definition of these two variables from every location.
2. Verify in `modules/runtime/chain/providers/cli.py` that the module-level `_CLI_KEY` variable will resolve to `None` when `ANTHROPIC_CLI_KEY` is absent, and confirm that the `_build_cmd` function does not append `--bare` when `_CLI_KEY` is falsy.
3. Verify in `modules/runtime/chain/adapter.py` that the provider resolution logic falls through correctly to the CLI provider when neither `ANTHROPIC_API_KEY` nor `ANTHROPIC_CLI_KEY` is set and `CHAIN_PROVIDER` is `cli`.
4. Start the local environment with `docker compose up -d`. Exec into the api container with `docker compose exec -it api bash` and run `claude login`. If the container lacks a browser, use the URL-copy flow: copy the printed URL, open it in a local browser, complete the OAuth flow, and paste the authorization code back into the container terminal.
5. After login completes, confirm that `/home/appuser/.claude/.credentials.json` exists inside the container and contains a refresh token.
6. Trigger a test generation request through the API and confirm it succeeds.
7. Run `docker compose restart api` and trigger another generation request to confirm credentials survived the restart.
8. Run `docker compose down && docker compose up -d` and trigger a third generation request to confirm credentials survived a full teardown via the named volume.

### Verify
- `docker compose exec api env | grep ANTHROPIC_CLI_KEY` returns nothing — the variable is not set
- `docker compose exec api env | grep CLAUDE_CREDENTIALS_JSON` returns nothing
- A generation request to the API returns a successful AI response after a fresh `docker compose up -d` without any manual credential intervention
- `docker compose down && docker compose up -d` followed by a generation request succeeds without re-login

---

## Task 4: Docker Healthcheck & Deploy Docs  [Effort: 0.5 days]

### What
The current Docker healthcheck (if any) only checks process liveness, passing even when auth is completely broken. This task wires the existing `/api/health/anthropic` endpoint as the Docker healthcheck target so auth failures surface in `docker ps` and Coolify's dashboard, adjusts the health endpoint to validate CLI auth when no API key is present, and documents the full VPS deployment and recovery procedures.

### Files
- **Modify**: `modules/observability/health.py` — Update the `/api/health/anthropic` handler to perform a lightweight CLI validation call instead of returning `"skipped"` when `CHAIN_PROVIDER=cli` and no `ANTHROPIC_API_KEY` is set
- **Modify**: `docker-compose.yml` — Add or replace the api service's `healthcheck` block to curl `/api/health/anthropic` with appropriate interval, timeout, retries, and start period
- **Modify**: `docker-compose.override.yml` — Add the same healthcheck configuration for local dev parity
- **Modify**: `DEPLOY.md` — Document the initial VPS setup procedure (volume creation, environment cleanup, container login) and the recovery procedure (volume deletion, re-seed, re-login)

### Steps
1. In `modules/observability/health.py`, find the conditional branch where the endpoint returns `{"status": "skipped"}` when no API key is configured. Replace that branch with logic that checks whether `CHAIN_PROVIDER` is set to `cli`, and if so, runs a lightweight CLI subprocess call (e.g., `subprocess.run(["claude", "-p", "ok", "--output-format", "text"], capture_output=True, text=True, timeout=15)`) to validate auth. The SDK `count_tokens` method cannot be used here because there is no `ANTHROPIC_API_KEY` under Option B — the CLI manages its own credentials. Return `{"status": "ok"}` on exit code 0, or `{"status": "degraded", "error": ...}` on failure.
2. In the production compose file, add a `healthcheck` block to the api service that runs `curl -f http://localhost:{port}/api/health/anthropic` with an interval of 60 seconds, a timeout of 10 seconds, 3 retries, and a start period of 120 seconds.
3. Add the identical healthcheck block to the local dev compose override file.
4. In `DEPLOY.md`, write an "Initial Setup" section covering: pull the latest code, run `docker compose up -d`, exec into the container, run `claude login`, verify with a test generation request, and confirm `docker ps` shows healthy status.
5. In `DEPLOY.md`, write a "Recovery" section covering: stop the containers, delete the credential volume with `docker volume rm`, restart with `docker compose up -d`, re-run `claude login`, and verify. Note that deleting the volume triggers the entrypoint to re-seed if `CLAUDE_CREDENTIALS_JSON` is still available as a fallback.
6. Test locally by running `docker compose up -d`, waiting for the start period, and confirming `docker ps` shows the api container as healthy. Then corrupt the credentials file inside the container and wait for three healthcheck cycles to confirm the container transitions to unhealthy.

### Verify
- `docker ps` shows the api container with a `(healthy)` status after successful login and start period
- After corrupting or removing credentials inside the container, `docker ps` transitions to `(unhealthy)` within 120 seconds (three 60-second cycles)
- `DEPLOY.md` contains both the initial setup and recovery procedures with concrete commands, not placeholders
- `curl http://localhost:{port}/api/health/anthropic` returns `{"status": "ok"}` when auth is valid and `{"status": "degraded"}` with an error message when auth is invalid