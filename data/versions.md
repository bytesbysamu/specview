# Deployment Versions — Fact Sheet

Injected into every implementation guide so generated code uses correct versions.

## Runtime
| Component | Version |
|-----------|---------|
| Python | 3.11 |
| Flask | 3.x |
| gunicorn | 23.x (`gthread` worker class, `--workers 1`) |
| Angular | 17 (standalone components, signals) |
| Node | 22 LTS |
| Ionic | 7.x + Capacitor 6.x (mobile projects) |

## AI
| Component | Value |
|-----------|-------|
| Claude model | `claude-sonnet-4-6` |
| Chain provider (local dev) | `cli` (subprocess via Claude Code CLI) |
| Chain provider (production) | `claude` (Anthropic SDK) |
| OpenClaw provider | `claude-cli/claude-sonnet-4-6` |
| CLI subprocess timeout | 3,600s |
| Angular HTTP timeout | 1,800,000ms (30 min) |
| Max tokens — task guides | 16,384 |
| Max tokens — bootstrap steps | 4,096 (analysis/epic) / 16,384 (architecture) |

## OpenClaw
| Component | Value |
|-----------|-------|
| Image | `ghcr.io/openclaw/openclaw:latest` |
| Gateway port | 18789 |
| Bridge port | 18790 |
| Workspace | `~/.openclaw/workspace/` |
| Config dir | `~/.openclaw/` |
| Telegram bot | `@ClawBoiSamBot` |

## Key Dependencies
| Package | Version |
|---------|---------|
| datamodel-code-generator | 0.45.0 |
| pydantic | 2.x |
| pytest | 8.x |
| @anthropic-ai/claude-code | latest (global npm install) |

## Paths (local dev)
| Purpose | Path |
|---------|------|
| SPEC_DOC_DIR (dev) | `/Users/sam/Projects/2026/spec-doc` |
| SPEC_DOC_DIR (Docker) | `/data/spec-doc` → host `~/Projects/spec-doc-data` |
| Projects | `$SPEC_DOC_DIR/projects/` |
| Context files | `$SPEC_DOC_DIR/*.md` |
| OpenClaw workspace | `~/.openclaw/workspace/` |
| Sam's projects (in container) | `/home/node/Projects/` |

## CI
- GitHub Actions: `.github/workflows/deploy.yml`
- Branch: `master` (PRs only, no direct push)
- DTO check: `make check-dtos` with `--target-python-version 3.9`
- Docker integration: `CHAIN_PROVIDER=mock`, `APP_ENV=test`
