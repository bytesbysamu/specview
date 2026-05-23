#!/bin/sh
# Fix Claude CLI credential permissions (volume may be owned by host uid)
chown -R appuser:appgroup /home/appuser/.claude 2>/dev/null || true
exec "$@"
