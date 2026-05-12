# Deploy

## Architecture overview

The API container runs Claude Code CLI under a non-root user (`appuser`). CLI
credentials are stored in a named Docker volume (`claude-credentials`) mounted
at `/home/appuser/.claude`. The Claude OAuth token in that volume auto-refreshes
on use, so you only need to log in once per volume lifetime.

The `/api/health/anthropic` endpoint runs a lightweight `claude -p ok` probe
when `CHAIN_PROVIDER=cli` is active. Docker (and Coolify) use this endpoint as
the container healthcheck — a degraded probe surfaces immediately in `docker ps`
and Coolify's dashboard instead of silently failing on generation requests.

---

## Initial VPS setup

```bash
# 1. Clone the repo
git clone <repo-url> /opt/specview
cd /opt/specview

# 2. Create the data directory
mkdir -p /opt/specview/data/projects

# 3. Build and start all services
docker compose build
docker compose up -d

# 4. Log in to Claude inside the API container (one-time per volume)
#    This writes OAuth credentials to the claude-credentials volume.
docker compose exec -it api claude login

#    Follow the browser OAuth flow that claude login prints.
#    When it completes, credentials are persisted in the named volume.

# 5. Verify the container reports healthy
docker ps
#    The api container STATUS column should show "(healthy)" within ~2 minutes.
#    You can also curl the probe directly:
curl http://localhost:3101/api/health/anthropic
#    Expected: {"status": "ok"}
```

---

## Claude credentials — how it works

- The named volume `claude-credentials` is mounted at `/home/appuser/.claude`
  inside the container. This is the same path the Claude CLI reads/writes.
- `claude login` writes an OAuth credentials file into the volume. The token
  includes a long-lived refresh token; the CLI silently refreshes it on each
  use, so you do not need to re-login unless you explicitly log out or delete
  the volume.
- On container restart or image rebuild the volume is preserved — credentials
  survive deployments automatically.

---

## Recovery — re-authenticating after credential loss

If the healthcheck starts returning `degraded` or you see auth errors in the
API logs, re-authenticate by replacing the volume:

```bash
cd /opt/specview

# 1. Stop services
docker compose down

# 2. Delete the credentials volume
docker volume rm specview_claude-credentials

# 3. Restart — the volume is recreated empty
docker compose up -d

# 4. Log in again
docker compose exec -it api claude login

# 5. Verify
curl http://localhost:3101/api/health/anthropic
```

---

## Verifying health

```bash
# Quick check — should return {"status": "ok"}
curl http://localhost:3101/api/health/anthropic

# Full container status (look for "(healthy)" in STATUS column)
docker ps

# Tail API logs for auth errors
docker compose logs -f api
```

---

## Updating the application

```bash
cd /opt/specview
git pull
docker compose build
docker compose up -d
# Credentials volume is preserved — no re-login required after a routine deploy.
```

---

## Data directory

Projects live at `/opt/specview/data/projects/` on the VPS.
Each project is a folder containing markdown files.

For local dev, the override mounts `./data` into the container automatically —
no extra configuration required.
