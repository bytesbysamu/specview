# SaaS Persistence — Analysis

## The Problem
spec-doc stores markdown on the filesystem with no user ownership and no version history. No DB layer means no entity can carry a `user_id` foreign key, blocking auth, monetisation, and every per-tenant query. The two-tier split (SQL for metadata, git for content) replaces this with purpose-fit storage before the retrofit cost becomes painful.

## Hard Constraints
- **Postgres contradicts the builder constraint** "No Redis, no Postgres, no external queue — in-process state or filesystem only." The dump proposes SQLite for dev and Neon for prod. Decide: SQLite-only for v1 (one consumer, no external deps), or explicitly override the constraint for SaaS mode.
- `/data/projects/<id>/` must be a Docker-mounted volume or all git repos vanish on container restart — not stated anywhere in the dump.
- `pygit2` requires native libgit2 in the Docker image; it is not a pure pip install.

## Open Questions
- **SQLite vs Neon for v1**: Is Postgres genuinely needed now, or does SQLite serve the single-consumer case until a second user exists? (a) SQLite only, revisit at first paid user. (b) Neon from day one, accept the external dep.
- **`User.plan` denorm**: What writes this field when a subscription changes — payment webhook, a cron, or nothing and it's always stale? No sync mechanism is defined.
- **Subscription + UsageCounter ownership**: Both land in `0001_initial_schema.py` but their SQLModel class definitions live in the monetisation brain dump. Which epic writes those Python files first, or do they co-author the migration?
- **Migration script trigger**: Manual CLI step, container-entrypoint guard, or CI job? The dump says "run once, verify, switch env" without defining who runs it or when.

## Dependencies & Sequencing
- Neon Auth JWT middleware (`g.current_user`) must exist before any route can resolve `user_id` — auth ships first or in the same PR.
- All four entity files (User, Project, Subscription, UsageCounter) must exist before `alembic revision --autogenerate` produces a correct `0001_initial_schema.py` — monetisation and persistence epics must coordinate on the migration file.
- `ProjectRepository.create()` atomicity depends on `git_store.init_repo()` being ready — git layer ships before or alongside the repository implementation.

## Explicitly Out of Scope
- **GitHub OAuth + push** — confirmed Phase 4; re-scopes when that brain dump exists.
- **`delete_file()` HTTP endpoint** — the git op ships for internal retry-recovery use, but no route for it belongs in this epic; that consumer doesn't exist yet.
- **FS repository as a post-migration fallback** — once the migration runs, the FS implementation should be deleted; keeping it is dead code and scope inflation.
- **"Connect GitHub" upsell framing** — used as design justification in the dump; zero deliverables here.