"""Usage metering — per-user daily call counters with free-tier caps.

SAAS_OPTIONAL package. The module is consumed via:
  - `modules.usage.decorators.check_usage_limit(feature)` on Flask handlers
  - `modules.usage.service.DAILY_FREE_TIER_LIMITS` to read free-tier caps

There are no HTTP routes in v1; all state lives in `usage_counter` whose
DDL is locked in `migrations/versions/0001_initial_schema.py`.
"""
