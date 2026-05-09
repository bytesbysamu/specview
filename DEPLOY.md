# Deploy

## VPS setup (one time)

```bash
# 1. Clone the repo
git clone <repo-url> /opt/specview
cd /opt/specview

# 2. Create the data directory and drop your projects in
mkdir -p /opt/specview/data/projects

# 3. Build and start
docker compose build
docker compose up -d
```

## Claude credentials (Coolify)

The API uses your Claude Max OAuth credentials for CLI calls. Set `CLAUDE_CREDENTIALS_JSON`
as an environment variable in Coolify — the container writes it to `~/.claude/.credentials.json`
at startup and auto-refreshes from there.

Get the value to paste into Coolify from your Mac:

```bash
security find-generic-password -s "Claude Code-credentials" -w
```

Copy the JSON output → Coolify service → Environment Variables → `CLAUDE_CREDENTIALS_JSON`.

The refresh token inside the JSON is long-lived. You only need to update this if you explicitly
log out of your Claude Max session.

App runs on port 80.

## Update

```bash
cd /opt/specview
git pull
docker compose build
docker compose up -d
```

## Data directory

Projects live at `/opt/specview/data/projects/` on the VPS.
Each project is a folder containing markdown files.

For local dev, override the data dir:

```bash
SPECVIEW_DATA_DIR=/path/to/your/spec-doc-data docker compose up -d
```
