## 6. Commit Plan (continued)

2. `feat(app): register SqlProjectRepository on app factory` — after **Step 2** — `create_app.py`
3. `refactor(projects): replace filesystem routes with repository+git_store` — after **Step 3** — `modules/projects/routes.py`
4. `refactor(task_gen): inject repo, drop projects_dir parameter` — after **Steps 4+5** — `modules/task_gen/routes.py`, `modules/task_gen/service.py`
5. `test(projects): replace service-layer tests with SqlProjectRepository tests` — after **Step 6** — `tests/test_project.py`
6. `remove(projects): delete filesystem service.py` — after **Step 7** — `modules/projects/service.py`
7. `test(structural): guard against direct modules.db imports in feature modules` — after **Step 8** — `tests/test_structural.py`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: The filesystem service tests (classes `TestFilenameToLabel`, `TestMakeId`, `TestListProjects`, `TestGetProject`, `TestCreateProject`, `TestUpdateFile`, `TestDeleteProject`, `TestRepairProject`) are removed; 8 repository unit tests + 3 route smoke tests + 1 structural test are added. Net change depends on the full size of the removed block in `test_project.py` — inspect lines 165–521 before starting and record the count. Structurally: all pre-existing tests not in `test_project.py` must remain green. Zero regressions outside this file is the acceptance criterion.

---

## 8. Rollback

- **Per-step**: every commit above is independently revertible with `git revert <sha>`. Steps 5 and 6 are order-sensitive: revert Step 6 (`git rm`) before reverting Step 5 (test update), otherwise `test_project.py` imports a deleted module.
- **Per-branch**: `git reset --hard <pre-task-sha>` on the feature branch, or delete the branch. No schema changes ship in this task (Alembic migration is Task 1); nothing to undo at the DB layer.

---

## 9. Deviations Allowed

- **`git_store.delete_repo` is absent** → implement `delete_project_route` without the git call; add `# TODO Task-2-followup: git_store.delete_repo(project.id)` inline; note in commit body. Do not invent the function.
- **`get_session()` in Task 1 is not a `@contextmanager`** (e.g., it's a generator for FastAPI `Depends`) → adapt `SqlProjectRepository` to use `with Session(engine) as session:` directly, importing `engine` from `modules.db.engine`. Note in commit body.
- **`Project.created_at` is timezone-aware** → update `_fmt_dt` to call `.astimezone(timezone.utc)` before strftime; this is a one-line fix, silent adaptation.
- **`task_gen` tests pass `projects_dir` to `start()` or `run_generation()`** → update those call-sites to pass a `MagicMock()` repo instead; note each changed call-site in the Step 4+5 commit body.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit body.
- **Side-effect required** (push, publish, schema change beyond what Task 1 already migrated) → **STOP**, mark `[REQUIRES APPROVAL]`, and ask.

---

## 10. Out of Scope

This task wires the SQL+git layer into existing routes and deletes the filesystem implementation. It does not touch anything that has no current consumer or belongs to a later epic.

- **Auth middleware / `g.current_user`** — the `_DEV_USER_ID = 1` constant is the explicit placeholder; replacing it is the auth epic's first act. Do not design a session-injection pattern here.
- **`0001_initial_schema.py` Alembic migration** — owned by Task 1 in coordination with the monetisation epic; this task only consumes the already-migrated schema.
- **`User` row seeding for dev** — Task 5 (migration script) creates the admin user; for tests the SQLite in-memory DB has no FK enforcement by default so `user_id=1` works without a real `User` row.
- **History / diff / revert HTTP endpoints** — Task 4 owns these; `git_store.get_history`, `get_diff`, `revert_file` are not called here.
- **Migration script** (`scripts/migrate_filesystem_to_git_db.py`) — Task 5; do not begin writing it here even if the pattern is obvious.
- **`repair_project` logic for non-template files** — the current implementation only regenerates the three standard template files; extending the repair list is a separate decision with no current consumer.
- **Angular changes** — the HTTP response shapes are backward-compatible; no frontend changes are needed in this task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for two-tier storage and atomic create
- [Epic](./epic.md) – Task scope and execution phases
- [Timeline](./timeline.md) – Update status to ✅ after verification passes