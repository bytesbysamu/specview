#!/bin/sh
# Fix Claude CLI credential permissions (volume may be owned by host uid)
chown -R appuser:appgroup /home/appuser/.claude 2>/dev/null || true

# Apply database migrations before the app boots, so the schema the code
# writes always exists (Never Again: "code wrote a column absent from
# migrations"). A failed migration must stop the deploy rather than serve
# against a stale schema.
echo "entrypoint: running alembic upgrade head"
alembic upgrade head

exec "$@"
