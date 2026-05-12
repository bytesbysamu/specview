#!/bin/sh
# Ensure the Claude credentials directory on the named volume is writable by appuser.
# Docker creates named volumes as root; the CLI needs write access for token refresh.
if [ -d /home/appuser/.claude ] && [ "$(stat -c '%u' /home/appuser/.claude 2>/dev/null || echo 0)" = "0" ]; then
    chown appuser:appgroup /home/appuser/.claude 2>/dev/null || true
fi

# Seed credentials from env var if provided AND no credentials file exists yet.
# This is a bootstrap fallback — the preferred path is `claude login` inside the container.
if [ -n "$CLAUDE_CREDENTIALS_JSON" ]; then
    mkdir -p /home/appuser/.claude
    if [ -f /home/appuser/.claude/.credentials.json ]; then
        echo "entrypoint: credentials file already exists on volume — preserving"
    else
        printf '%s' "$CLAUDE_CREDENTIALS_JSON" > /home/appuser/.claude/.credentials.json
        echo "entrypoint: seeded credentials from CLAUDE_CREDENTIALS_JSON"
    fi
fi

exec "$@"
