# Specview — Comprehensive Status & Documentation

**Date:** 2026-05-11
**Author:** Sam + Claude Code
**Purpose:** Master reference document — where we stand, what's built, what's next.

---

## What Specview Is

A self-hosted spec generation tool. Users paste a braindump; an AI chain generates analysis, epic, architecture, timeline, and implementation guide. The experience is designed around a newspaper editorial aesthetic — "opening the app should feel like opening a newspaper."

**Stack:** Flask API (Python 3.11) + Angular 17 SPA (signals, no NgRx) + static landing page (nginx:alpine), deployed via Docker Compose on Coolify VPS.

---

## Architecture

```
specview/
├── api/                     — Flask API (Python 3.11)
│   ├── modules/
│   │   ├── runtime/chain/   — AI adapter layer (the ONLY AI call boundary)
│   │   │   ├── adapter.py   — generate(), stream(), rewrite() — DEFAULT_MODEL: claude-opus-4-6
│   │   │   └── providers/   — cli.py (subprocess), claude.py (SDK), mock.py (testing)
│   │   ├── ai/              — Prompts, workflows, routes, services
│   │   │   └── routes/text.py — bootstrap-project endpoint (braindump → full spec set)
│   │   ├── auth/            — JWT auth (bcrypt passwords, HS256 tokens)
│   │   ├── data/            — Projects (filesystem), context files
│   │   ├── billing/         — Stripe integration
│   │   ├── usage/           — Rate limiting, daily quotas
│   │   └── quality/         — Structural tests (import boundaries)
│   ├── migrations/          — Alembic (PostgreSQL on Neon)
│   └── e2e/                 — End-to-end test features
├── web-ng/                  — Angular 17 SPA
│   ├── src/app/
│   │   ├── app.component.ts   — Root component (all state as signals)
│   │   ├── app.component.html — 505 lines, single-page shell
│   │   ├── services/
│   │   │   ├── projects.service.ts    — All HTTP calls, Promise<T> via firstValueFrom
│   │   │   ├── project-teaser.ts      — Teaser extraction from file content
│   │   │   └── section-taxonomy.service.ts — Section classification logic
│   │   └── app.config.ts     — Bootstrap configuration
│   └── src/styles.css         — 1,581 lines, full design system
├── landing/                 — Static marketing page
│   ├── index.html           — 308 lines, main landing
│   ├── style.css            — 1,172 lines, shared tokens
│   ├── playground.html      — 2,304 lines, live component reference ("our Figma")
│   └── app-overview.html    — Design mockup with 3 iterations (A/B/C)
├── plugin/                  — Claude Code plugin
│   └── references/          — 4 convention files (angular, flask, chain, testing)
├── .claude/
│   ├── agents/              — 4 specialist agents
│   └── skills/              — 9 executable skills
└── data/projects/           — 37 braindump projects (spec storage)
```

---

## AI Chain — How Spec Generation Works

The chain adapter (`api/modules/runtime/chain/adapter.py`) is the ONLY AI call boundary. Feature modules import ONLY from `adapter.py`, never from providers directly. This is enforced by `test_structural.py`.

**Provider:** `CHAIN_PROVIDER=cli` in Docker. The CLI provider shells out to `claude` CLI with `--model claude-opus-4-6`. On the host, CLI uses the macOS keychain for auth. In Docker, `CLAUDE_CREDENTIALS_JSON` env var provides OAuth credentials (must be refreshed when expired).

**Bootstrap pipeline** (`POST /api/ai/text/bootstrap-project`):
1. Braindump → Analysis (chain generates analysis.md)
2. Braindump + Analysis → Epic (chain generates epic.md)
3. Braindump + Epic → Architecture (chain generates architecture.md)
4. Analysis + Epic + Architecture → Timeline (chain generates timeline.md)

Each step feeds the next. The pipeline runs in a background thread; frontend polls for status.

**Text operations** (per-file AI ops):
- Expand, Compress, Clarify, Simplify, TL;DR, Bullets, Brainstorm, Style, Rewrite
- Each produces a diff view; user can Apply or Dismiss

---

## Design System — The Newspaper Aesthetic

**Philosophy:** Dieter Rams minimalism + editorial newspaper layout.

- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace create structure; shadows do not exist (one modal exception)
- Ink on paper: cream `#FFFEF9` not white, near-black `#121212` not black
- Interaction is quiet — hover is a whisper of background
- Color = state, not category. Green = running, red = error, grey = idle

**Token system:**
```css
:root {
  --bg: #FFFEF9;        --ink: #121212;
  --ink-light: #5A5A5A; --ink-muted: #999999;
  --border: #DFDFDF;    --border-dark: #121212;
  --accent: #567B95;    --red: #C41E3A;
  --serif: 'Playfair Display';
  --body: 'Source Serif 4';
  --sans: 'Source Sans 3';
}
```

**Status bar colors** (playground 5.7):
- Idle: `#1a6b30` (dark green) — "system ready"
- Active: `#7a5800` (dark amber) + shimmer gradient — "generating"
- Success: `#1a6b30` (dark green) — "done"
- Failure: `#C41E3A` (red) — "error" + retry button

**Section colors** (header titles only, not on cards):
- Active: `#22A66A` (green)
- Specced: `#567B95` (blue)
- Ready to build: `#7B6BAE` (purple)
- Braindumps: `#A08060` (brown)

---

## Frontend — Current State (as of PR #40)

### Overview page (all-sections view)
- **Masthead:** "Spec Doc" edition, date, "Specview" title (64px Playfair), italic tagline (Source Serif 4)
- **Section nav:** Sticky, 3px ink top border, text-only tabs with grey pill count badges
- **Status bar:** Inline between nav and search, always visible, 4 states (idle/active/success/failure)
- **Search:** Filter input + "N projects" count label
- **Section groups:** Each section has colored overline title + 2px ink underline + pill count badge
- **Card grid:** `auto-fill minmax(280px, 1fr)`, vertical-only separators (`border-left`), 20px 24px padding
- **Hero grid:** Active section uses `2fr 1fr 1fr` — lead story 28px title, 4-line teaser, secondary 16px title
- **Featured first card:** Each section's first card gets 17px title + 3-line clamp
- **Teasers:** Source Serif 4 at 14px, real content from braindump.md first sentence (teaser_chars=500)
- **Badges:** Grey pill for file count, state-colored for status (NEW=red, COMPLETE=green, READY=blue)

### Single-section view (clicking a tab)
- **3-column newspaper layout:** `.file-grid repeat(3, 1fr)` with `.file-column` + `border-right` dividers
- **Column headers:** Playfair 15px title + count badge

### Expanded panel (clicking a project)
- **Sidebar:** Sticky, file nav, generate button, AI ops chips, status indicator
- **Main content:** 2-column markdown (Source Serif 4, Playfair headings)
- **Editor toolbar:** Sticky, with op chips + style presets + apply/dismiss/copy
- **Diff view:** Red/green left borders for remove/add blocks

---

## Backend — Current State

### API Routes (8 blueprints)
| Route | Purpose |
|---|---|
| `/api/auth` | Login (JWT), token creation |
| `/api/projects` | CRUD, list with teasers, file save |
| `/api/context` | Builder/principles/codebase/references files |
| `/api/ai/text/*` | Bootstrap pipeline, brainstorm, text ops (expand/compress/etc) |
| `/api/billing` | Stripe subscription check |
| `/api/usage` | Rate limiting, daily quotas |
| `/api/templates` | Project templates |
| `/api/health` | Health check |

### Key conventions
- `@require_auth` then `@check_usage_limit("scope")` on every AI route
- Service functions own transaction boundaries — never `session.commit()` in a route handler
- Background jobs: `threading.Thread` + module-level dict for state
- `ProviderError(msg, status)` is the only exception type from chain calls

### Database
- PostgreSQL (Neon, pooled connection in production)
- Alembic migrations in `api/migrations/`
- Models: User, Usage (SQLModel)

---

## Plugin System — Agents & Skills

### Agents (4)
| Agent | Handles |
|---|---|
| `chain-agent` | Chain adapter, prompts, workflow steps, providers |
| `spec-backend` | Flask routes, SQLModel models, migrations, services |
| `spec-frontend` | Angular components, signals, services, templates |
| `chain-developer` | Cross-layer features, full-stack coordination |

Each agent loads reference files from `plugin/references/` automatically.

### Skills (9)
| Skill | When to use |
|---|---|
| `/dev-build` | Check backend imports or frontend build |
| `/dev-test` | Run pytest (scoped to nearest module) |
| `/dev-migrate` | Scaffold + apply Alembic migration |
| `/dev-review` | 3-agent parallel code review before PR |
| `/spec-pipeline` | Braindump → full spec set via bootstrap API |
| `/impl-guide` | Epic + architecture → implementation guide |
| `/exec-guide` | Execute implementation guide tasks via agents |
| `/triage-projects` | Archive stale, set priorities, sync to container |
| `/brainstorm` | Enhance braindump with AI brainstorm |

### Routing rule (from CLAUDE.md)
Before acting on ANY request, check whether a skill or agent applies. Do not bypass — agents load conventions automatically.

---

## All 37 Projects — Inventory

### Fully Specced (all spec files + exec-guide-summary)
| Project | Files | Priority | Status |
|---|---|---|---|
| UX: Reader, Text Ops & Navigation | 10 | 1 | Specced |
| Specview SaaS Go-to-Market | 9 | 1 | Specced |
| Landing Polish (Newspaper) | 9 | — | Complete (exec-guide ran) |
| UX: App Grid Polish | 9 | — | Complete (exec-guide ran) |
| UX Polish — Newspaper Feel, Phase 2 | 9 | — | Specced |

### Partially Specced (6-8 files)
| Project | Files | Notes |
|---|---|---|
| App UI Mockups | 8 | Mock design iterations, impl guide executed |
| UX: Landing & Grid Polish | 6 | In progress (PR #40) |
| Events | 8 | Specced |
| Landing Polish (Phase 3) | 7 | Specced |
| Landing v2 Playground | 8 | Design system reference |
| Prepper | 8 | New, untracked |

### Braindumps Only (1-2 files, not yet specced)
Text Ops Thread UI, Specview Open Source Release, Specview Self-Hosted Packaging, SpecDocV2, 6-Month Plan & Strategy, Financing Plugin, ClawBoi, Howdays, OpenClaw, Spec-Doc Legacy, Speedback, Constellation, WardrobAI, Claude Code Guide, Relationship Wrapped, Bubls, Mobbin MCP, IonStarter, Spec-Doc API, Spec-Doc Context, Super App Vision, CI & Test Quality

---

## Docker — Local Dev Setup

```bash
# Start all services
docker compose up -d

# Ports (from override):
# web:     http://localhost:8095
# landing: http://localhost:8096
# api:     internal (proxied through web)

# Rebuild after code changes:
docker compose build web && docker compose up -d web     # frontend
docker compose build api && docker compose up -d api     # backend
docker compose build landing && docker compose up -d landing  # landing

# Re-auth Claude CLI in container (when OAuth token expires):
export CLAUDE_CREDENTIALS_JSON="$(security find-generic-password -s 'Claude Code-credentials' -w)"
docker compose up -d api

# Mockup dev server (no Docker rebuild needed):
cd landing && python3 -m http.server 8097

# Angular dev server with Docker API proxy:
cd web-ng && ng serve  # reads proxy.conf.json → localhost:8095
```

---

## Git State

**Current branch:** `feat/ux-overview-polish`
**Open PR:** #40 — "UX: Overview polish — mockup design applied to app"
**Commits ahead of master:** 40

### Active branches
| Branch | Purpose |
|---|---|
| `feat/ux-overview-polish` | Current — mockup design → live app |
| `feat/ux-polish-newspaper` | Newspaper feel phase 2 |
| `feat/landing-v2-promote` | Landing page v2 to production |
| `feat/phase4-quality-reliability` | Hardening pass |
| `feat/editor-brainstorm-specgen` | Brainstorm → spec gen flow |
| `ux/reader-textops-navigation` | Reader UX overhaul |

### 12 Dependabot branches queued for review

---

## What Was Built This Session (2026-05-10 → 05-11)

### Mockup iteration (`landing/app-overview.html`)
1. Three design variants: A (baseline), B (breathing room), C (hero grid)
2. Promoted C as working mock with functional nav filter + search
3. ClawBoi gap analysis — 10 experiments documented (E1-E10)
4. Playground color audit — state not category principle
5. Applied all experiments: serif teasers, heavy headers, hero grid gap, featured cards, badges, status bar
6. Reduced horizontal lines (cut redundant borders)
7. Added vertical-only card separators
8. Status bar with playground 5.7 colors (4 states, click to cycle)

### Applied to Angular app
1. Grid: 280px min, vertical rules, 20px 24px padding, no grey fill
2. Section headers: colored titles via `[data-section]`, 2px ink underline, pill counts
3. Typography: Source Serif 4 teasers at 14px, featured first card (17px)
4. Status bar: inline between nav and search, always visible, idle state
5. Badges: grey count pills, state-colored status badges
6. Hero grid: `2fr 1fr 1fr` for Active section
7. Real teasers from braindump.md first sentence (teaser_chars 300→500)
8. Overline: 9px muted in app (was 11px red)
9. Tagline: Source Serif 4 italic (was Source Sans 3)
10. Search count always visible
11. Gen dot: white #fff with border-radius
12. Section-link: flex layout for pill alignment

### Chain changes
- DEFAULT_MODEL: `claude-sonnet-4-5` → `claude-opus-4-6`
- CLI provider now passes `--model` flag to claude CLI

---

## What's Next — Prioritized Backlog

### High Priority
1. **Merge PR #40** — All overview polish changes ready
2. **Landing page improvements** (Tasks 5-9 from UX Landing & Grid Polish epic):
   - Output card grid (replace flat list with 5 `.output-card` elements)
   - Demo strip section (miniaturized app UI mockup)
   - Step editorial bodies
   - Masthead tagline font change
   - Section nav "Demo" link
3. **Fix bootstrap API** — Background thread crashes silently (gunicorn worker restart?)
4. **Reader UX overhaul** — `ux/reader-textops-navigation` branch

### Medium Priority
5. **Landing v2 promotion** — New design to production
6. **Phase 4: Quality & Reliability** — Test coverage, CI, error handling
7. **Dependabot cleanup** — 12 branches queued

### Low Priority / Backlog
8. **Open Source Release packaging**
9. **SaaS Go-to-Market** (pricing, onboarding)
10. **Self-hosted packaging** (Docker Compose distribution)
11. **Dark mode contrast fixes** (icon contrast floor, modal shadow)
12. **Mobile/responsive improvements**

---

## Key Decisions Log

| Decision | Value | Date | Rationale |
|---|---|---|---|
| Default model | claude-opus-4-6 | 2026-05-10 | Higher quality spec generation |
| Card borders | Vertical only, no horizontal | 2026-05-10 | Newspaper column feel |
| Color philosophy | State not category | 2026-05-10 | Playground audit: green=running, red=error, grey=idle |
| Status bar | Inline, always visible | 2026-05-10 | Editorial ticker, not web app overlay |
| Teaser font | Source Serif 4, 14px | 2026-05-10 | ClawBoi body font, newspaper feel |
| Hero grid | 2fr 1fr 1fr for Active only | 2026-05-11 | ClawBoi headline pattern, lead story prominence |
| Overline in app | 9px muted (not red) | 2026-05-10 | App is tool, not marketing |
| Badge system | Grey=count, red=NEW, green=DONE, blue=ACTION | 2026-05-10 | Playground 5.16 pattern |
| teaser_chars | 500 (was 300) | 2026-05-10 | Braindumps need more chars for first prose sentence |
| Nav icons | Text-only (no SVG) | 2026-05-10 | 12px SVGs add noise, text labels are distinctive |

---

## Credentials & Access

| Service | Credentials |
|---|---|
| App login | `sam@specview.app` / `salt` |
| Claude CLI (host) | macOS keychain (`Claude Code-credentials`) |
| Claude CLI (Docker) | `CLAUDE_CREDENTIALS_JSON` env var (auto-refreshed from keychain) |
| Database | PostgreSQL on Neon (connection string in docker-compose.yml) |
| JWT | Secret in `JWT_SECRET` env var (container) |

**OAuth token refresh:** When Claude CLI fails with 401 in Docker:
```bash
export CLAUDE_CREDENTIALS_JSON="$(security find-generic-password -s 'Claude Code-credentials' -w)"
docker compose up -d api
```
