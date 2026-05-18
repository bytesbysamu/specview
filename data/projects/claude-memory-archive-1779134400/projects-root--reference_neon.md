---
name: Neon DB connection
description: Shared Neon Postgres instance used by trendfy and Springular — connection details and tables
type: reference
---

**Neon pooler endpoint:** `ep-lively-feather-agg1dzjp-pooler.c-2.eu-central-1.aws.neon.tech`
**Database:** `neondb`
**User:** `neondb_owner`

Tables in public schema (as of 2026-04-06):
- `email_signups` — trendfy landing page waitlist
- `users`, `user_roles`, `refresh_tokens`, `password_reset_token` — Springular auth (legacy)
- `user_usage`, `webhook_events` — humanize-me (legacy)
- Various twin_* tables — other project

**How to apply:** When adding new tables for trendfy, use this same Neon instance. Connection string is in wardrobai/.env as DATABASE_URL.
