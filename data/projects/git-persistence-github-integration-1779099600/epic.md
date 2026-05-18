# 🎯 Epic: Git Persistence — GitHub Integration

## Business Value

Specview generates spec documents through an AI pipeline that takes 1–3 minutes per run. Today, those files live on ephemeral container storage with no off-box backup. A single `docker compose up` with a fresh image wipes every project — hours of generated content gone with no recovery path. This is the number-one trust blocker for any user considering Specview for real work. No one adopts a documentation tool that can lose their documentation.

GitHub integration transforms Specview from a fragile local tool into a durable, portable SaaS. Every file write pushes to the user's own GitHub repository. Users can browse their specs on GitHub, clone them locally, and share the repo — all in a standard format they already understand. If Specview's infrastructure burns down, users still have every spec in their GitHub account. "Your specs live in your GitHub repo" is the single most powerful trust signal a solo-founder SaaS can offer, and it costs nothing in storage — GitHub private repos are free.

This also unlocks a defensible positioning advantage. Competing spec tools lock content inside proprietary formats. Specview stores plain markdown in a git repo the user owns. That transparency converts skeptics and reduces churn — users who can leave easily tend to stay longer. For monetization, GitHub sync becomes the natural gate between a free tier (local-only, ephemeral) and a paid tier (durable, portable, GitHub-backed).

## Scope

### What This Epic Covers

- **GitHub authentication flow** — User connects their GitHub account from Specview settings; Specview stores credentials and can exchange them for API tokens on demand
- **Repository provisioning** — On first connect, Specview creates (or adopts) a single private repository on the user's GitHub account with a defined directory structure
- **Async push-on-write** — Every local file commit triggers a background push to GitHub; no user-facing latency added to the pipeline
- **Sync state tracking** — Database columns and a UI indicator that show whether each project is synced, pushing, or failed
- **Schema migration** — Additive columns on User and Project tables to support GitHub connection state and sync tracking
- **Push-on-connect for existing projects** — When a user connects GitHub, all their current projects push to the new repo immediately

### What This Epic Does NOT Cover

- ❌ **Pull-based recovery / restore endpoint** — This is a sync engine, not a push feature; ship push first, prove the repo format in production, then scope restore as its own epic (re-scope trigger: first actual data-loss incident post-push)
- ❌ **Import from existing GitHub repos** — Different user flow, different conflict model, different UX; out of scope until user requests justify it
- ❌ **Merge UI for external edits** — If users edit files directly on GitHub, Specview's version wins with a logged warning; a merge UI is deferred until branch protection proves insufficient
- ❌ **Collaboration features (PRs, Issues, shared repos)** — Marketing upside but not engineering scope; re-scope when multi-user demand materializes
- ❌ **Persistent volume fix** — This is a one-line infrastructure change that should ship independently and immediately, not gated behind this epic
- ❌ **GitHub App vs OAuth App decision** — The auth mechanism is an architectural choice documented in [Solution Architecture](./architecture.md); this epic is agnostic to the auth provider chosen

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **GitHub Auth + Token Exchange** — OAuth flow, callback handling, token storage on User model, "Connect GitHub" settings page | None | — | 3 days | High |
| 2 | **DB Schema Migration** — Additive columns on User table (installation/token fields, repo name, connected timestamp) and Project table (remote push SHA, sync status, last push timestamp, last push error) | None | With Task 1 | 1 day | High |
| 3 | **Repo Provisioning** — Create private `specview-projects` repo on connect (or detect existing), write repo-level metadata, push all existing user projects to establish baseline | Tasks 1, 2 | — | 2 days | High |
| 4 | **Async Push-on-Write** — Background push triggered after every local `git_store` commit; in-process queue with retry logic; sync state updates in DB; Contents API per file | Tasks 1, 2, 3 | — | 3 days | High |
| 5 | **Sync Status Indicator** — UI component showing per-project sync state (synced / pushing / failed with retry action); reads sync columns from existing project API | Task 4 | — | 1 day | Low |

## Success Criteria

- ✅ A user can connect their GitHub account from Specview settings in under 60 seconds
- ✅ Running a full pipeline (5–6 files) results in all files appearing in the user's GitHub repo within 30 seconds of pipeline completion
- ✅ The GitHub repo structure matches the defined directory layout: one folder per project, one markdown file per spec, plus repo-level metadata
- ✅ A container restart with no persistent volume does NOT lose GitHub-pushed data — user's specs remain accessible on GitHub
- ✅ A failed GitHub push is retried automatically and surfaces a visible "sync failed" indicator in the UI — no silent data loss
- ✅ Disconnecting GitHub stops syncing but preserves all local project data intact
- ✅ Sync state in the database accurately reflects reality: no project stuck in `pushing` state after worker completion

## Related Documents

- [Analysis](./analysis.md) — Problems driving this epic; data-loss scenarios and infrastructure gaps identified
- [Solution Architecture](./architecture.md) — System design; auth mechanism decision, push strategy, conflict handling, schema details
- [Timeline](./timeline.md) — Status tracking and phase delivery dates