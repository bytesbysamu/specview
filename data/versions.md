# Deployment Versions — Fact Sheet

Injected into every implementation guide so generated code uses correct versions.

## Runtime

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| Flask | 3.x |
| Angular | 17 (standalone components, signals) |
| Node | 22 LTS |

## AI

| Component | Value |
|-----------|-------|
| Claude model (default) | `claude-sonnet-4-6` |
| Chain provider (local dev) | `cli` — subprocess via `claude` CLI |
| Chain provider (Docker) | `cli` — always, never SDK |
| Chain provider (tests) | `mock` |
| CLI subprocess timeout | 3,600s |
| Max tokens — task guides | 8,192 |
| Max tokens — bootstrap architecture | 16,384 |
| Max tokens — other bootstrap steps | 4,096 |

## Key Dependencies

| Package | Version |
|---------|---------|
| SQLModel | 0.x |
| pydantic | 2.x |
| pytest | 8.x |
| alembic | 1.x |

## Paths (local dev, no Docker)

| Purpose | Path |
|---------|------|
| SPEC_DOC_DIR | `/Users/sam/Projects/specview/data` |
| Projects | `/Users/sam/Projects/specview/data/projects/` |
| Context files | `/Users/sam/Projects/specview/data/*.md` |
| API entry point | `/Users/sam/Projects/specview/api/app.py` |
| API port | `5001` |
| Frontend port | `4201` |

## Paths (Docker)

| Purpose | Path |
|---------|------|
| SPEC_DOC_DIR | `/data/spec-doc` |
| Projects | `/data/spec-doc/projects/` |

## CI

- GitHub Actions: `.github/workflows/` (if present)
- Branch: `master` — PRs only, no direct push
- Tests: `pytest api/ -q` must pass before merge
- Provider in CI: `CHAIN_PROVIDER=mock`
