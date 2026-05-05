# spec-doc — Monorepo Structure Refactor

> **MERGED** into `braindump-saas-operations.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P4 — cosmetic; does not block any other capability.
> **Effort**: ~half day (file moves + import path updates + structural test).
> **Blocks**: nothing.
> **Depends on**: nothing.
> **Siblings**: none — independent housekeeping.
> **Risk**: high churn on file paths; defer until a quiet week. Best done after
>          a major release rather than in the middle of an active sprint.

## What

Two structural moves that have been discussed and deferred:
1. **Lift `docs/` to the repo root** — spec documents for spec-doc itself should live at `spec-doc/docs/`, not `spec-doc/api/docs/`
2. **Move `projects/` into `api/resources/projects/`** — project data is a runtime resource of the API, not a peer of it

Both moves are path changes only. No logic changes. The goal is a monorepo shape that matches how the code actually works.

### Current shape (confusing)

```
spec-doc/
├── api/                    ← Flask backend
│   ├── modules/
│   ├── dtos/
│   ├── docs/               ← spec docs live here, buried in api/
│   └── CLAUDE.md
├── web/                    ← Angular frontend
└── projects/               ← runtime project data lives at root, not in api/
    ├── workflows-.../
    └── braindump-*.md
```

`api/` has a `SPEC_DOC_DIR` env var pointing to `../` — the API reaches outside its own directory to find projects. This is the root cause of the awkward path handling.

### Target shape (clear)

```
spec-doc/
├── api/
│   ├── modules/
│   ├── dtos/
│   └── resources/
│       └── projects/       ← projects live inside api/ as a resource
├── web/
└── docs/                   ← spec docs at root, next to api/ and web/
    ├── analysis.md
    ├── epic.md
    ├── architecture.md
    └── timeline.md
```

`SPEC_DOC_DIR` default changes from `../` to `./resources` in the API.

### 1. Move projects/

```bash
mkdir -p api/resources
mv projects/ api/resources/projects/
```

Update `api/.env`:
```bash
SPEC_DOC_DIR=/Users/sam/Projects/2026/spec-doc/api/resources
```

Update `api/config.py`:
```python
PROJECTS_DIR = os.environ.get(
    "SPEC_DOC_DIR",
    os.path.join(os.path.dirname(__file__), "resources"),
)
```

The `PROJECTS_DIR` path is already injected everywhere via `config.py` — no route or service changes needed.

### 2. Move api/docs/ to docs/

```bash
mv api/docs/ docs/
```

No code references `api/docs/` — it's documentation only. Update any cross-references in `CLAUDE.md` files.

Update root `CLAUDE.md` to point to `docs/` for spec documents.

### 3. .gitignore — keep project data out of git

```gitignore
# api/resources/projects/ — runtime data, not source code
api/resources/projects/*/
!api/resources/projects/.gitkeep
```

Project directories are user-created runtime data, not checked into version control. The `.gitkeep` ensures the directory exists for fresh clones.

### 4. Docker — update COPY and volume mount

```dockerfile
# Dockerfile — after move
COPY api/ .
# resources/projects/ is a volume, not baked into image
```

```yaml
# docker-compose.yml — volume mount
volumes:
  - projects_data:/app/resources/projects
```

### 5. CI — update stub path

```yaml
# .github/workflows/deploy.yml
- name: Create project stub
  run: |
    mkdir -p /tmp/spec-doc-stub/api/resources/projects
    echo '[]' > /tmp/spec-doc-stub/api/resources/projects/.gitkeep
```

```yaml
env:
  SPEC_DOC_DIR: /tmp/spec-doc-stub/api/resources
```

### 6. Context files — builder, principles, codebase, references

Currently loaded from `SPEC_DOC_DIR/context/`. After the move, `context/` lives at `api/resources/context/`. No code change — the path is derived from `SPEC_DOC_DIR` in `modules/context/service.py`.

## Why now

The current layout requires the API to reach outside its own directory for runtime data (`SPEC_DOC_DIR=../`). This breaks when the API runs in Docker (no `../` to escape to). The `projects/` move makes the containerized deployment correct by default.

The `docs/` move is cosmetic but matters for the 6-month plan: as spec-doc gets used for more projects, having the product's own spec documents visible at the root is important for onboarding.

## What's missing

One decision: **migration of existing project data**. The `api/resources/projects/` path only applies to fresh installs unless existing data is moved. Options:
- (a) `mv projects/ api/resources/projects/` — one-time migration, update env var on server
- (b) Keep `SPEC_DOC_DIR` pointing to current location, only change default — no migration needed
- (c) Support both paths (env var check with fallback) — backwards compatible but messy

Option (a) is correct but requires a maintenance window on the server. Option (b) is a non-breaking first step.

## Explicitly out of scope

- Separate repository for spec documents — monorepo is the right shape
- Database-backed project storage — filesystem is sufficient and simpler to back up
- Renaming `api/` or `web/` directories — too many path references to change safely
- Splitting frontend and backend into separate deployable packages — single container deployment is the target
