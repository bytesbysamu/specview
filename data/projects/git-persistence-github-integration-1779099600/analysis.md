# 🔍 Git Persistence — GitHub Integration — Analysis

## The Problem
Specview's generated specs live in ephemeral container storage with no persistent volume in production. A single `docker compose up` wipes all user data. A complete local git layer exists (8 operations, pygit2-backed) but has zero off-box durability — it's version control that can't survive a restart.

## Hard Constraints
- No Redis, no external queue — background push must use in-process state (`threading.Lock` + module-level dict) or `threading.Thread`
- GitHub API: 5000 req/hr per installation token — not a real bottleneck at current scale
- pygit2 is already abstracted behind `modules.data.git_store` — GitHub adapter must slot in at that boundary, not below it
- Neon Postgres is the DB — schema migrations must be Alembic-managed
- Single gunicorn worker assumed — in-process queue dies on worker restart; unsynced writes must be recoverable from DB state alone

## Open Questions
- **Push granularity**: Per-file (Contents API, simple, 6 calls/pipeline) vs per-commit (Git Data API, 1 call, complex tree-building)? → Start per-file; batch is premature optimization for a solo-user product
- **Queue durability**: Brain dump says "async background worker" but constraints forbid external queues. What happens to in-flight pushes when gunicorn restarts? → `sync_status = pending` rows in Neon ARE the queue; a startup sweep retries them
- **Conflict policy**: "Specview wins, force push" works today. But the moment a user edits on GitHub, you silently destroy their changes. → Decide now: block GitHub edits via branch protection, or detect and warn? Don't ship silent overwrite.
- **One repo vs N repos**: Brain dump recommends one repo. Correct — but the directory scheme (`slug-timestamp/`) means project renames or slug collisions need a policy. What happens to the GitHub path when a project is renamed locally?

## Dependencies & Sequencing
- **Persistent volume (Phase 1) is independent** — do it today, no code changes, pure `docker-compose.yml` fix
- **GitHub App registration** blocks all API work — do it before writing any adapter code, because the permission scopes shape the implementation
- **Token exchange service** blocks push and provisioning — and installation tokens expire hourly, so the refresh logic must exist before any GitHub write
- **Schema migration** (`github_installation_id`, `sync_status`) blocks sync tracking but not the OAuth flow itself — can run in parallel with App setup
- **Pull recovery (Phase 4) depends on push (Phase 3) being stable** — you can't test restore without real GitHub data to restore from

## Explicitly Out of Scope
- **Import from external GitHub repos** — different data model, no `project.json` guarantee, unknowable directory structure. Revisit if users ask.
- **Merge UI for conflicts** — requires diff3, UI work, and a policy nobody needs yet. Revisit when a second user edits on GitHub and complains.
- **Collaboration features (PRs, Issues, shared repos)** — the brain dump lists these as benefits but they're GitHub-native; Specview builds nothing. Don't let them creep into the epic.
- **Multi-repo-per-user** — one repo. If someone hits 100+ projects, that's a success problem to solve later.
- **Backfill job (Phase 5)** as a separate phase — fold it into Phase 3. When a user connects GitHub, push everything they have. It's the same code path. A separate phase is artificial.