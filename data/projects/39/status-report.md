# Specview — Weekly Status Report
*Week of 5 May – 9 May 2026 · Generated 2026-05-09*

---

## Summary

Specview went from zero to a fully deployed, AI-powered spec generation tool in five days. The week covered: initial build and deploy, Angular 19 rewrite, AI skill layer, thin-API migration, landing page, and a UX reader overhaul — all shipped to production via CI.

---

## Day-by-Day

### Tuesday 5 May — Init, Deploy, Angular 19

- **Project initialised** — openclaw-style markdown viewer for spec-doc projects
- **Newspaper redesign** — Playfair serif, cream bg, 3-col grid, expanded panel
- **UX polish pass** — sticky nav, file teasers, active file indicator, even column fill
- **Self-contained Docker build** — API source bundled, web baked into nginx; no host volume
- **Coolify deploy** — removed host port bind; Coolify handles ingress via Traefik
- **185 projects loaded** — context files, section nav, tabs UI added
- **Data housekeeping** — archived 90 stale projects; 54 active remain
- **Real-time search bar** added
- **Angular 19 app (web-ng)** — full TypeScript rewrite with signals, no NgRx
- **Auth** — swapped to bcrypt + PyJWT; wired Neon DB; removed SKIP_AUTH
- **Projects load immediately** on login via `effect()`; polling starts after

### Wednesday 6 May — CLI Provider, Editor, Plugin

- **CLI provider wired** — incremental spec generation and live bootstrap polling
- **Editor toolbar** — brainstorm Q&A, spec-gen from brainstorm, undo/redo, live status bar
- **AI text ops panel redesign** — chips, thinking dots, result card with latency display
- **chain-agent-plugin added** — references, agents, skills, hook, and `cli.py` routing
- **Landing page** launched on port 8096
- **Generate Guide endpoint** — single `implementation-guide.md` for full epic
- **Plugin clarified** — reframed as general-purpose Claude Code Provider Plugin
- PR #1 merged: `feat/editor-brainstorm-specgen`

### Thursday 7 May — Thin-API Phase 2, Skills Layer, Landing Polish

- **Thin-API Phase 2** — zero-Python AI layer; AI services migrated to plugin-driven generation
- **7 skills, 4 agents** wired in `.claude/`: `dev-build`, `dev-test`, `dev-migrate`, `dev-review`, `spec-pipeline`, `impl-guide`, `exec-guide`; agents: `chain-agent`, `spec-backend`, `spec-frontend`, `chain-developer`
- **Generic skill route** added — sync/async skill execution layer
- **exec-guide** auto-runs `dev-test` + `dev-review` after task execution
- **Track A + B migration** — retired Python prompt building
- **`/impl-guide` skill** — turns epic + architecture into implementation guide
- **Auto-routing** — CLAUDE.md dispatch rules + trigger-phrase skill descriptions
- **CLI fixes** — clean `.claude-docker` dir; `--bare` flag when CHAIN_AGENT + CLI_KEY both set
- **Docker fixes** — removed `.claude.json` volume mount (was causing JSON corruption from write races); `.claude.json` remounted read-only
- **nginx timeout** increased to 300s for Claude CLI calls
- **Landing** — hosted tier pricing surface added; visual simplification; full-screen sections; ClawBoi alignment + Lucide icons
- Braindumps added for 19 projects

### Friday 8 May — CI, UX Reader Overhaul, Data Bake

- **CI simplified** — dropped separate generate jobs; generate inline per job
- **DTOs** — generated Python DTOs from openapi.yaml in CI and in Docker; gitignored generated files
- **Frontend CI** now triggered when `api/openapi.yaml` changes
- **Node.js 24** — opted in via CI
- **`impl-guide` fix** — write permission issue resolved; `epic_guide` prompt enforced `impl-guide` output structure
- **UX reader overhaul (PRs #27, #28)** — sidebar-first layout, taxonomy tabs, status bar, animations, Lucide icons, text ops and navigation
- **All projects committed to `data/projects/`** — baked into production image; local dev uses volume mount via override
- Dependabot grouped into one PR per ecosystem; GitHub Actions bumped

---

## Key Decisions This Week

| Decision | Rationale |
|---|---|
| `CHAIN_PROVIDER=cli` always | Container can't reach Anthropic directly; all AI routes via CLI provider |
| Signals-only Angular | No BehaviorSubject, no Observable for local state; `signal<T>()` + `computed()` |
| Projects = folders of `.md` files | No database for spec storage; `data/projects/{slug}/` on disk |
| Plugin references = single source of truth | Convention rules live once in `plugin/references/*.md`; agents cite them |
| No direct push to master | All changes via PR; CI must pass |
| Bake data into image | Simplifies deploy; no volume management on VPS |

---

## Stats

- **90 commits** since Monday
- **4 major features shipped**: Angular 19 rewrite, AI skill layer, thin-API migration, UX reader overhaul
- **7 PRs merged**: #1 editor/brainstorm, #2 landing pricing, #3 Phase 4 quality, #7 & #21 Dependabot, #27 & #28 UX reader
- **7 skills** + **4 agents** active in plugin
- **185 projects** indexed; 90 archived

---

## Current State

- Live on VPS: Coolify/Traefik handles routing — no fixed host ports; Flask API internal on port 3101
- Local dev: `docker compose up -d` (override maps 8095 → nginx web proxy, 8096 → landing)
- CI: GitHub Actions — pytest suite (701 tests, 0 failures as of Phase 4)
- All AI calls route via `CHAIN_PROVIDER=cli` + `chain-agent`

---

## Open Questions / Next

- Extract `server.js` (legacy Express path) fully in favour of Flask, or keep as dev-only utility?
- Modularise `api/modules/ai/` further as AI workflow types grow
- CI-triggered deploy (currently manual `git pull + docker compose build` on VPS)
- Run `spec-pipeline` on any new feature braindump before writing code
- Use `exec-guide` to dispatch implementation tasks to specialist agents
