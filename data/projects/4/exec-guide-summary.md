# exec-guide summary — Auth Reliability & Credential Persistence

**Date:** 2026-05-12
**Tasks run:** 4
**Tasks passed:** 4 / 4
**Tests:** passed (chain: 50 passed, observability: 79 passed — 129 total)
**Review:** 3 critical (all fixed), 5 warnings (2 addressed, 3 deferred)

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: CLI Error Signal Recovery | complete | `api/modules/runtime/chain/providers/cli.py`, `api/modules/runtime/chain/providers/tests/test_cli.py` |
| Task 2: Credential Volume & Entrypoint Guard | complete | `docker-compose.yml`, `docker-compose.override.yml`, `api/entrypoint.sh` |
| Task 3: Environment Cleanup & Container Auth Session | complete | `docker-compose.override.yml`, `.env`, `api/modules/runtime/chain/adapter.py` |
| Task 4: Docker Healthcheck & Deploy Docs | complete | `api/modules/observability/health.py`, `api/modules/observability/tests/test_health.py`, `docker-compose.yml`, `DEPLOY.md` |

## Post-review fixes

| Critical | Fix applied |
|----------|-------------|
| Dead `_CLI_KEY` / `--bare` code in cli.py | Removed `_CLI_KEY`, `_build_env()`, all `--bare` branches. Docstring updated. |
| Zero test coverage for CLI health probe | Added 5 tests: cli-ok, cli-degraded, cli-timeout, skipped, haiku-model-check |
| Health probe consuming generation credits at 1,440/day | Changed to `--model claude-haiku-4-5`, interval 60s -> 300s (288 calls/day on flat rate) |

## Deferred warnings

| Warning | Reason deferred |
|---------|-----------------|
| `scripts/credentials-refresh.sh` is orphaned | Out of scope — delete in follow-up cleanup |
| `entrypoint.sh` CLAUDE_CREDENTIALS_JSON fallback is confusing | Harmless no-op, serves as bootstrap escape hatch |
| Hardcoded DATABASE_URL and JWT_SECRET in docker-compose.yml | Pre-existing, tracked in P1 (SaaS Launch Readiness) Task 4 |

## Test results

```
129 passed, 0 failed, 1 warning (0.39s)

chain module:     50 passed (cli provider, adapter, context, file parser, structural)
observability:    79 passed (errors, health, logging, sentry)
```

## Review findings

3 critical issues found and fixed in a second pass. 5 warnings — 2 addressed (stale docstring, haiku model), 3 deferred as noted above.

## Next steps

- Run `/commit` to commit all changes
- `docker compose build api && docker compose up -d api` to test locally
- `docker compose exec -it api claude login` to establish persistent session
- Run the 7-phase local verification from the braindump before merging to master
- Delete `scripts/credentials-refresh.sh` in a follow-up
