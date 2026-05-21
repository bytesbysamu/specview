# Git Persistence — GitHub Integration

## The Problem

Specview generates valuable spec documents — analysis, epic, architecture, implementation guides — through an AI pipeline that takes 1-3 minutes per run. These generated files live on the VPS filesystem inside Docker containers. When the container restarts, rebuilds, or the VPS migrates, all project data vanishes. Users lose hours of generated content with no recovery path.

### What breaks today

**Container ephemeral storage.** The production `docker-compose.yml` defines only one named volume (`claude-credentials`). The project data directory `/data/spec-doc` is not mounted to a persistent volume. Every `docker compose up -d` with a fresh image starts with empty project storage. The dev override mounts `~/Projects/specview/data` but production has no equivalent.

**No backup mechanism.** There are zero automated snapshots of the project filesystem, no database backup strategy, no version retention beyond the local git history that lives inside the same ephemeral container. If the Docker volume is deleted, it's total data loss — filesystem, git history, and SQLite database all gone in one shot.

**Dual-write consistency gaps.** The create flow writes to the filesystem first, then attempts a DB insert. If the DB insert fails, the filesystem write still stands — the project exists on disk but not in the database. There's no repair mechanism to reconcile these states. The code even acknowledges this with a comment: "DB row can be back-filled by a repair job" — but no such repair job exists.

**No export or restore.** There's no endpoint to export a project as a tarball, no bulk backup API, no restore workflow. If a user wants to back up their specs, they have to manually copy files from the server.

**Orphaned git repos.** When a project is deleted, the DB row is removed but the on-disk git repository stays forever. The code explicitly notes: "git_store.delete_repo does not yet exist (Task-2 follow-up); the on-disk repo is intentionally orphaned." Over time this accumulates garbage.

### Data loss scenarios

- Container restart without persistent volume → total loss of all projects
- Neon Postgres connection drops → API reads/writes fail, no graceful degradation
- Accidental project deletion → permanent, no undo, orphaned git repo remains
- Corrupted .git directory → project becomes unreadable, no backup to restore from
- VPS provider migration → filesystem not portable, requires manual intervention

## What Already Exists

Specview has a surprisingly complete local git layer. The problem isn't missing version control — it's missing durability.

### git_store service (8 operations, fully implemented)

Located at `api/modules/data/git_store/service.py`, using pygit2:

1. **init_repo(project_id)** — Creates per-project directory, initializes a working repository (not bare), pins HEAD to `refs/heads/main`, creates empty initial commit, returns SHA.

2. **write_file(project_id, filename, content, msg)** — Writes content to disk, stages with `repo.index.add()`, commits immediately with the given message, returns new commit SHA.

3. **read_file(project_id, filename, ref="HEAD")** — Reads file content at a specified commit/ref, returns UTF-8 decoded text.

4. **list_files(project_id, ref="HEAD")** — Returns sorted list of blob filenames at top level.

5. **get_history(project_id, filename, limit=20)** — Walks commit log topologically, returns commits that touched the filename. Each entry: `{sha, message, timestamp}`.

6. **get_diff(project_id, filename, from_sha, to_sha)** — Returns unified diff between two commits.

7. **revert_file(project_id, filename, to_sha)** — Forward commit that restores file to state at `to_sha`. Never rewrites history — the code explicitly notes this is "safe for any future GitHub mirror."

8. **delete_file(project_id, filename, msg)** — Removes file from working tree, stages removal, commits.

### HTTP routes exposing git operations

- `GET /<project_id>/files/<filename>/history?limit=20` → commit history
- `GET /<project_id>/files/<filename>/diff?from_sha=X&to_sha=Y` → unified diff
- `POST /<project_id>/files/<filename>/revert` → forward-commit revert

### Project SQL model (Neon Postgres)

```
Project table:
  id              int (PK)
  user_id         int (FK → user.id)
  name            str
  slug            str (unique, indexed)
  git_repo_path   str          ← stores filesystem path
  latest_commit_sha  str|null  ← updated after every write
  file_count      int          ← updated after every write
  created_at      datetime
  updated_at      datetime
```

The atomic create contract: `SqlProjectRepository.create()` inserts the DB row and calls `git_store.init_repo()` inside one try/except. Git failure rolls back the DB insert.

### Module isolation

A structural test (`test_pygit2_isolation.py`) enforces that feature code only imports from `modules.data.git_store` package root — never directly from pygit2. This means the git backend can be swapped (to GitPython, a remote service, or GitHub API) without touching any feature module.

## The Vision

Every Specview user gets a GitHub repository. Every file write pushes to GitHub. Full version history lives on GitHub — durable, portable, accessible outside Specview. The Neon DB tracks sync state.

### User experience

1. User signs up for Specview, connects their GitHub account (OAuth).
2. Specview creates a private repo: `{username}/specview-projects` (or user picks a name).
3. User creates a project, pastes a braindump. The pipeline generates analysis, epic, architecture, guide.
4. Each generated file is committed locally AND pushed to GitHub within seconds.
5. User can browse their specs on GitHub, clone locally, share the repo.
6. If the VPS burns down, user reconnects GitHub → Specview pulls all projects from the repo.

### Repository structure on GitHub

```
specview-projects/
├── payment-gateway-redesign-1779099600/
│   ├── project.json
│   ├── braindump.md
│   ├── analysis.md
│   ├── epic.md
│   ├── architecture.md
│   ├── implementation-guide.md
│   └── timeline.md
├── auth-security-overhaul-1779100000/
│   ├── project.json
│   ├── braindump.md
│   └── analysis.md
└── .specview/
    └── config.json          ← repo-level metadata (user, plan, created)
```

Each project is a directory. Each spec is a markdown file. The structure mirrors what's already on disk — zero transformation needed.

### Why GitHub (not S3, not custom git server)

- Users already have GitHub accounts. No new account friction.
- GitHub renders markdown natively. Users can read specs without Specview.
- Free private repos. No storage cost for Specview.
- GitHub API is well-documented, stable, rate-limited generously (5000 req/hr authenticated).
- Pull-based recovery: if Specview dies, users still have all their data.
- Collaboration: users can share repo access, get PRs, use GitHub Issues alongside specs.

## Architecture Sketch

### Authentication: GitHub App (not OAuth App)

A GitHub App is better than an OAuth App because:
- Fine-grained permissions (only `contents: write` on specific repos)
- Installation-level tokens (not user-level — survives password changes)
- Higher rate limits (5000 → installation token, vs 5000 → user token)
- Can create repos on behalf of user

Flow:
1. User clicks "Connect GitHub" in Specview settings.
2. Redirect to GitHub App installation page.
3. User installs the Specview app on their account (or selected repos).
4. GitHub redirects back with installation ID.
5. Specview stores `github_installation_id` on the User model.
6. For API calls, Specview exchanges installation ID for a short-lived token (1 hour).

### Repo provisioning

On first project creation (or manual trigger):
1. Check if user has a `specview-projects` repo. If not, create it via GitHub API.
2. Store `github_repo_full_name` on User model (e.g., `bytesbysamu/specview-projects`).
3. Add initial commit with `.specview/config.json`.

### Push strategy: async push-on-write

Every `git_store.write_file()` already creates a local commit. The addition:

```python
# After local commit succeeds:
async_push_to_github(project_id, commit_sha)
```

This queues a background task that:
1. Gets an installation token for the user.
2. Uses GitHub Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`) to push the file.
3. Or uses Git Data API for batch commits (more efficient for multi-file pipeline runs).
4. Updates `Project.remote_push_sha` in Neon DB on success.
5. On failure: retries 3x with exponential backoff, then marks project as `sync_failed`.

**Why async, not sync:**
- Pipeline generates 5-6 files in sequence. Blocking on GitHub push after each would add 1-2s per file.
- User doesn't need to wait for GitHub — local storage is the hot path.
- Background worker can batch multiple files into one GitHub commit.

### Conflict handling

Specview is the single writer. Users should not edit files directly on GitHub (though they can read them). If a conflict is detected:
- Specview's version wins (force push the file).
- A warning is logged but not surfaced to user.
- Future: detect external edits and offer merge UI.

### Pull-based recovery

When a user reconnects (new VPS, fresh install, or disaster recovery):
1. Specview reads the GitHub repo contents via API.
2. For each project directory: create local project, write files, init git repo.
3. Insert Project rows in Neon DB.
4. User sees all their projects restored.

## Integration with Neon DB

### Schema changes

**User table — add:**
```sql
ALTER TABLE "user" ADD COLUMN github_installation_id BIGINT;
ALTER TABLE "user" ADD COLUMN github_repo_full_name VARCHAR(255);
ALTER TABLE "user" ADD COLUMN github_connected_at TIMESTAMP;
```

**Project table — add:**
```sql
ALTER TABLE project ADD COLUMN remote_push_sha VARCHAR(40);
ALTER TABLE project ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending';
  -- Values: 'synced', 'pending', 'pushing', 'failed'
ALTER TABLE project ADD COLUMN last_push_at TIMESTAMP;
ALTER TABLE project ADD COLUMN last_push_error TEXT;
```

### Sync state machine

```
pending → pushing → synced
                  ↘ failed → pushing (retry)
```

- `pending`: local commit exists but not yet pushed to GitHub
- `pushing`: background worker is actively pushing
- `synced`: `remote_push_sha == latest_commit_sha`
- `failed`: push failed after retries, `last_push_error` has details

### Status bar integration

The existing status bar component can show sync state:
- Idle: "Synced with GitHub" (green)
- Pushing: "Pushing to GitHub..." (animated)
- Failed: "GitHub sync failed — retry" (red, clickable)

## Migration Path

### Phase 1: Persistent volume (immediate fix)

Before any GitHub work, fix the container persistence:
```yaml
# docker-compose.yml (production)
volumes:
  spec-doc-data:
    driver: local

services:
  api:
    volumes:
      - spec-doc-data:/data/spec-doc
```

This stops the bleeding — projects survive container restarts.

### Phase 2: GitHub App setup

1. Register a GitHub App (`specview-app`) with permissions: `contents: write`, `metadata: read`.
2. Add callback URL for installation flow.
3. Implement token exchange service.
4. Add "Connect GitHub" button in user settings.
5. Store installation ID on User model.

### Phase 3: Repo provisioning + push

1. On GitHub connect: create `specview-projects` repo if missing.
2. Add `remote_push_sha` and `sync_status` columns to Project table.
3. After every `git_store.write_file()`: queue async push.
4. Background worker pushes to GitHub via Contents API or Git Data API.
5. Update sync status in DB.
6. Show sync indicator in status bar.

### Phase 4: Pull recovery

1. Add `/api/github/restore` endpoint.
2. Reads GitHub repo, creates local projects, backfills DB.
3. Called on user login if local projects are empty but GitHub has content.

### Phase 5: Backfill existing projects

1. For users who connected GitHub before having projects: push all existing projects.
2. One-time migration job: iterate all projects for a user, push each to GitHub.
3. Mark all as `synced` after successful push.

## Open Questions

- Should each project be a separate GitHub repo, or one repo with all projects as directories? One repo is simpler (1 repo per user, not N repos), but large repos get slow. Recommendation: one repo, revisit if users hit 100+ projects.
- Should Specview support importing from an existing GitHub repo? (e.g., user has markdown specs elsewhere and wants to bring them into Specview)
- Should the push be per-file (Contents API) or per-commit (Git Data API)? Per-commit is more efficient for pipeline runs (5-6 files at once) but more complex to implement.
- Rate limiting: GitHub allows 5000 requests/hour per installation. A pipeline run that generates 6 files = 6 API calls. At 5000/hr, that's ~830 pipeline runs/hr per user — more than enough. But batch operations reduce this further.
- Should users be able to disconnect GitHub and keep their data? Yes — disconnecting should only stop syncing, not delete local data.

## What This Enables

- **Durability**: Projects survive any infrastructure failure. GitHub is the backup.
- **Portability**: Users own their data in a standard format (markdown in git). No lock-in.
- **Collaboration**: Share the repo, get PRs, use GitHub Issues.
- **Transparency**: Users can see exactly what Specview stores — it's just markdown files in a repo.
- **Recovery**: Fresh Specview instance + GitHub connection = all projects restored in minutes.
- **Trust**: "Your specs are in your GitHub repo" is a powerful trust signal for a SaaS product.
