#!/bin/sh
# Ensure the Claude credentials directory on the named volume is writable by appuser.
# Docker creates named volumes as root; the CLI needs write access for token refresh.
if [ -d /home/appuser/.claude ] && [ "$(stat -c '%u' /home/appuser/.claude 2>/dev/null || echo 0)" = "0" ]; then
    chown appuser:appgroup /home/appuser/.claude 2>/dev/null || true
fi

exec "$@"
