# 🎯 Epic: Git Persistence — GitHub Integration

## Business Value

Specview's core product — AI-generated spec documents — takes 1-3 minutes of pipeline time per run and represents hours of accumulated project thinking. Today, all of that lives on ephemeral container storage with zero durability. A routine deploy, a container restart, or a VPS migration wipes every project for every user. This isn't a theoretical risk; it's the current production reality. No paying user will trust a tool that can't keep their work.

GitHub as the durable store solves durability and creates a trust moat. "Your specs live in your own GitHub repo" is a fundamentally different value proposition than "your specs live on our server." Users own their data in a standard format (markdown in git), can read it without Specview, can share it, can clone it. This eliminates the single biggest objection a technical buyer has to any SaaS tool: vendor lock-in. It also unlocks stateless containers — deploy anywhere, scale horizontally, recover from any failure in seconds — which directly reduces infrastructure cost and operational risk as the user base grows.

The GitHub integration is a prerequisite for every growth milestone. Without durable storage there is no basis for paid tiers, no basis for team features, and no credible onboarding story. This epic is not a feature — it is the foundation that makes Specview a real product.

## Scope

### What This Epic Covers

- **GitHub App authentication flow** — User connects their GitHub account via App installation; Specview stores installation credentials and provisions a private repository
- **Schema migration for sync state** — New columns on User and Project models, plus a `pending_writes` table that acts as a write-ahead log in Neon
- **Durable write path** — Every file write lands in Neon WAL immediately, then pushes to GitHub asynchronously via background worker; a write is not complete until GitHub confirms
- **Cache-through read path** — Local filesystem is an ephemeral cache; cache misses lazy-fetch from GitHub transparently, enabling fully stateless container boots
- **Existing project backfill** — One-time migration that pushes all current project data to GitHub after a user connects, ensuring no content is stranded on the old ephemeral-only path

### What This Epic Does NOT Cover

- ❌ **Merge UI for external edits** — Overwrite-and-log is acceptable for v1; revisit only if 409 conflict rate warrants it
- ❌ **Multi-repo support** — One repo per user with project directories; revisit at 100+ projects per user
- ❌ **Full git history mirroring** — GitHub receives flat commits per file push; local history is richer; accept the divergence
- ❌ **Collaboration or shared repos** — Single-owner only; out of scope until multi-user lands
- ❌ **Horizontal scaling of the background worker** — One container, one worker; revisit at 50+ concurrent users
- ❌ **Status bar UI for sync state** — Visual indicators are a follow-on; this epic delivers the backend contract the UI will consume

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **GitHub App Registration & OAuth Flow** | None | — | 2 days | High |
| 2 | **Schema Migration & Pending Writes Table** | None | with #1 | 1 day | High |
| 3 | **Durable Write Path (Neon WAL + GitHub Push)** | #1, #2 | — | 3 days | High |
| 4 | **Cache-Through Read Path** | #3 | — | 2 days | High |
| 5 | **Existing Project Backfill** | #3, #4 | — | 1 day | Low |

**Task 1** delivers the GitHub App (manual registration + installation callback endpoint), token exchange, and repo provisioning. Nothing else can talk to GitHub without this.

**Task 2** adds `github_installation_id`, `github_repo_full_name`, and `github_connected_at` to User; adds `remote_push_sha`, `sync_status`, `last_push_at`, and `last_push_error` to Project; creates the `pending_writes` table. Runs in parallel with Task 1 since it touches DB, not GitHub.

**Task 3** is the core deliverable: file writes go to Neon WAL first (durable in ~5ms), then a background worker pushes to GitHub with retry and state-machine transitions (`pending → pushing → synced | failed`). This is where data stops being ephemeral.

**Task 4** makes container restarts invisible: cache miss on local filesystem triggers a GitHub fetch, writes to local cache, and serves. No bulk restore, no boot-time sync — first access after restart pays ~200-300ms, then cached.

**Task 5** migrates all projects that existed before GitHub was connected. Lower priority because it only runs once per user and can be triggered manually if the automated path isn't ready.

## Success Criteria

- ✅ A file written through the pipeline is recoverable from GitHub after the container is destroyed and restarted with an empty filesystem
- ✅ `pending_writes` rows reach zero (all synced) within 60 seconds of pipeline completion under normal conditions
- ✅ Container cold boot serves a previously-created project's files without any pre-population step
- ✅ A user with no GitHub connection experiences zero regressions — all existing flows work unchanged
- ✅ Failed GitHub pushes retry automatically and surface `sync_status = 'failed'` with actionable error text in `last_push_error`
- ✅ The `git_store` module boundary is preserved — no feature code imports GitHub or pygit2 directly (enforced by existing isolation test)

## Related Documents

- [Analysis](./analysis.md) — Problems and data-loss scenarios driving this epic
- [Solution Architecture](./architecture.md) — Storage model, write/read paths, sync state machine, schema design
- [Timeline](./timeline.md) — Task status and progress tracking