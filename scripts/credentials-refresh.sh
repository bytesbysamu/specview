#!/bin/sh
# Pulls Claude credentials from the macOS Keychain and writes them to .env
# so docker compose picks up CLAUDE_CREDENTIALS_JSON automatically.
#
# Run from anywhere; .env is always written to the repo root.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CREDS=$(security find-generic-password -s "Claude Code-credentials" -w)
printf 'CLAUDE_CREDENTIALS_JSON=%s\n' "$CREDS" > "$REPO_ROOT/.env"
echo "Written to $REPO_ROOT/.env"
