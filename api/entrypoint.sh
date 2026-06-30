#!/bin/sh
# Fix Claude CLI credential permissions (volume may be owned by host uid)
chown -R appuser:appgroup /home/appuser/.claude 2>/dev/null || true

# Apply database migrations before the app boots, so the schema the code
# writes always exists (Never Again: "code wrote a column absent from
# migrations"). A failed migration must stop the deploy rather than serve
# against a stale schema.
#
# GUARD: the shared oll_core DB is dual-owned — the remote Core also owns and
# migrates it. Running `alembic upgrade head` on every specview boot is a
# dual-owner deploy-outage risk. Gate it behind RUN_MIGRATIONS (default off) so
# Core stays the sole migrator of the shared schema. Set RUN_MIGRATIONS=1 only
# when specview owns its own DB.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "entrypoint: running alembic upgrade head"
  alembic upgrade head
else
  echo "entrypoint: skipping alembic (RUN_MIGRATIONS!=1; Core owns the shared oll_core schema)"
fi

exec "$@"
