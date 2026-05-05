It seems you need to grant write permission to the projects directory. The file I'm writing is the implementation guide to:

`projects/v2-spec-doc-backend-foundation-project-management-1776868958774/task-2-project-crud-module.md`

Could you approve the write? Here's a summary of what the guide covers:

**Key decisions made during research:**

1. **`specs` vs `files` key** — The references.md contract says `files`, but the Angular frontend (`projects.service.ts`) uses `specs` with a `label` field. I chose to match Express behavior so the frontend works unchanged.

2. **3-file module pattern** — `dto.py` (Pydantic v2), `service.py` (pure functions, zero Flask imports, `projects_dir: Path` injected), `routes.py` (thin Blueprint controller). Follows the bubls pattern from references.md.

3. **Test strategy** — Two test files: service layer tests (22 tests with `tmp_path`, no Flask dependency) and route layer tests (13 tests with Flask test client, `monkeypatch` to redirect `PROJECTS_DIR`). Mirrors the Express integration tests.

4. **~200 lines of module code** + ~250 lines of tests, within the port budget.

The guide has all 10 required sections with complete, verbatim code for every file — ready for an executor to run end-to-end.