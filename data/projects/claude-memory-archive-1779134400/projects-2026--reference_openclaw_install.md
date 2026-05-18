---
name: OpenClaw install location and entry points
description: Where Sam's OpenClaw gateway lives (path, Control UI URL, setup notes file) so future sessions can find and maintain it without rediscovering the install.
type: reference
---

- Repo: `~/Projects/openclaw` (cloned from `github.com/openclaw/openclaw`)
- Image: `ghcr.io/openclaw/openclaw:latest` (pre-built pull, not locally built)
- Compose: always include both files — `docker compose -f docker-compose.yml -f docker-compose.extra.yml ...`
  - `docker-compose.extra.yml` bind-mounts `~/.claude` + `~/.claude.json` so the containerized `claude` CLI can use Sam's Max plan OAuth credentials
- Control UI: http://127.0.0.1:18789/ (gateway token in `~/Projects/openclaw/.env` as `OPENCLAW_GATEWAY_TOKEN`)
- Gateway config on host: `~/.openclaw/openclaw.json`
- **Setup notes (authoritative for this install):** `~/Projects/openclaw/SETUP-NOTES.md` — includes how the Max plan + `claude-cli` backend was wired, the token-cost minimization knobs, the patched `scripts/docker/setup.sh` line 516, and the reapply checklist for container recreation.

When making changes to this install, always check `SETUP-NOTES.md` first to avoid regressing the careful Max-plan tuning.
