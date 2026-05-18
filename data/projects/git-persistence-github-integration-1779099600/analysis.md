# 🔍 Git Persistence — GitHub Integration — Analysis

## The Problem
Specview's generated specs live on ephemeral container storage with no backup. A `docker compose up` on a fresh image wipes all project data — files, git history, SQLite. A complete local git layer exists (8 ops, pygit2, module-isolated) but nothing pushes off-box, so durability is zero.

## Hard Constraints
- No Redis, no external queue — background push must be in-process (threading / module-level dict + Lock per builder profile)
- pygit2 is abstracted behind `modules.data.git_store` — GitHub layer must not leak into feature modules
- Neon Postgres is the DB — schema migrations must be additive (no destructive ALTER on live tables)
- Single gunicorn + nginx deploy via Coolify — no sidecar worker process
- GitHub API: 5000 req/hr per installation token; pipeline = ~6 files, so ceiling is ~830 runs/hr/user

## Open Questions
- **GitHub App vs OAuth App?** Brain dump chose App for fine-grained perms and installation tokens — but App requires JWT signing, webhook verification, and a registered callback. OAuth App is three env vars and a token. For < 100 users on a solo-founder SaaS, OAuth App likely ships a week faster. Decision needed before Phase 2.
- **Push mechanism without a queue?** "Async push-on-write" is specified but the stack forbids Redis/Celery. Options: (a) `threading.Thread` fire-and-forget per commit, (b) in-process queue with `queue.Queue` + single daemon thread, (c) `BackgroundTasks` if migrating to Starlette. Pick one — it shapes retry logic and failure handling.
- **Per-file (Contents API) vs per-commit (Git Data API)?** Pipeline writes 5-6 files sequentially. Contents API = 6 round-trips, trivial code. Git Data API = 1 commit, complex tree-building. Recommend: start Contents API, batch later only if latency matters.
- **Force-push on conflict — acceptable?** Brain dump says "Specview wins, log a warning." This silently destroys any edit a user makes on GitHub. Either enforce read-only via branch protection or surface a visible warning. Silent data loss undermines the trust pitch.

## Dependencies & Sequencing
- Persistent volume (Phase 1) is **not a GitHub feature** — it's an infrastructure fix that blocks nothing and should ship independently, today
- GitHub App/OAuth registration is a manual step that gates all integration code
- Schema migration (`github_installation_id`, `sync_status` columns) must land before push logic
- Push layer depends on token exchange service — build auth first, push second
- Pull recovery (Phase 4) depends on a stable push format — cannot build restore before the repo structure is proven in production

## Explicitly Out of Scope
- **Pull-based recovery / restore endpoint** — this is a sync engine, not a push feature. Ship push, prove the format, then scope restore as its own epic. Re-scope trigger: first actual data loss incident post-GitHub-push.
- **Import from existing GitHub repos** — different user flow, different conflict model, different UX. Re-scope trigger: user requests.
- **Merge UI for external edits** — brain dump already deferred it; keep it deferred. Re-scope trigger: branch protection proves insufficient.
- **Collaboration features (PRs, Issues, shared repos)** — marketing copy, not engineering scope. Re-scope trigger: multi-user demand.
- **Phase 5 backfill migration job** — premature. No users have GitHub connected yet. Just push-on-connect for existing projects as part of Phase 3. Re-scope trigger: users exist who connected before push was live.
- **Persistent volume fix (Phase 1)** — ship it now as a one-line infra PR, not as part of this epic.