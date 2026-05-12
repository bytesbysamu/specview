#!/bin/sh
# Write Claude credentials from env var if provided.
# This allows OAuth token auto-refresh inside the container without a host volume mount.
# Set CLAUDE_CREDENTIALS_JSON in Coolify (or docker-compose environment) to the full
# JSON from: security find-generic-password -s "Claude Code-credentials" -w
if [ -n "$CLAUDE_CREDENTIALS_JSON" ]; then
    mkdir -p /home/appuser/.claude
    if [ -f /home/appuser/.claude/.credentials.json ]; then
        echo "entrypoint: credentials file already exists on volume — preserving existing credentials"
    else
        printf '%s' "$CLAUDE_CREDENTIALS_JSON" > /home/appuser/.claude/.credentials.json
    fi
fi

exec "$@"
