# specview / spec-doc

## What this is

Specview is a self-hosted spec generation tool. Users paste a braindump; an AI chain
generates analysis, epic, architecture, timeline, and implementation guide.
The stack is a Flask API + Angular 17 SPA, deployed via Docker Compose (Coolify on VPS).

## Stack

```
specview/
├── api/                     — Flask API (Python 3.11)
│   └── modules/
│       ├── runtime/chain/   — AI adapter layer (the only AI call boundary)
│       ├── ai/              — Prompts, workflows, routes, services
│       ├── auth/            — JWT auth
│       └── data/            — Context files
├── web-ng/                  — Angular 17 SPA (signals, no NgRx)
├── landing/                 — Static marketing page (nginx:alpine)
├── plugin/                  — Claude Code plugin (references, agents, skills, hook)
└── .claude/                 — Active plugin wiring (agents, skills, settings)
```

## Agent and skill routing — always check first

Before acting on any request, check whether a skill or agent applies:

- Any build, compile, or import check → use `/dev-build`
- Any test run, pytest, failing test → use `/dev-test`
- Any database schema change, new column, new table → use `/dev-migrate <desc>`
- Any code review, pre-PR check, diff review → use `/dev-review`
- Any spec generation, braindump processing → use `/spec-pipeline <project>`
- Any Flask route, SQLModel model, migration, service → delegate to `spec-backend` agent
- Any Angular component, signal, service, template → delegate to `spec-frontend` agent
- Any chain adapter, prompt, workflow step, provider → delegate to `chain-agent`
- Cross-layer or unclear scope → delegate to `chain-developer` agent

Do not bypass these — the agents load conventions automatically. Doing it yourself skips the reference files and risks convention violations.

## Non-negotiable rules

- `CHAIN_PROVIDER=cli` always — never use the SDK provider in Docker.
- Never push directly to `master` — always a PR, CI must pass first.
- Run `pytest` in `api/` before any merge.
- Never import from `modules/runtime/chain/providers/*` in feature modules — import only from `chain/adapter.py`. Enforced by `test_structural.py`.
- Angular state is signals only — no BehaviorSubject, no Observable for local state.

## Available skills (invoke with /skill-name)

| Skill | When to use |
|-------|-------------|
| `/dev-build` | Check backend imports or frontend build |
| `/dev-test` | Run pytest (scoped to nearest module) |
| `/dev-migrate <desc>` | Scaffold + apply an Alembic migration |
| `/dev-review` | 3-agent parallel code review before a PR |
| `/spec-pipeline <project>` | Run braindump → full spec set via bootstrap API |

## Available agents (delegate with /agents or use in tasks)

| Agent | Handles |
|-------|---------|
| `chain-agent` | Chain adapter, prompts, workflow steps, provider changes |
| `spec-backend` | Flask routes, SQLModel models, Alembic migrations, services |
| `spec-frontend` | Angular components, signals, services, templates, polling |
| `chain-developer` | Cross-layer features, full-stack coordination |

Agents load their reference files (`plugin/references/`) automatically.

## Key conventions (quick reference)

**Backend:**
- Blueprints in `modules/{name}/routes/{name}.py`, registered with prefix `/api/{name}`.
- `@require_auth` then `@check_usage_limit("scope")` on every AI route.
- Service functions own transaction boundaries — never `session.commit()` in a route handler.
- Background jobs: `threading.Thread` + module-level dict for state.

**Frontend:**
- `signal<T>()` for all state, `computed()` for derivations.
- All HTTP in `ProjectsService` returning `Promise<T>` via `firstValueFrom()`.
- `@if` / `@for` control flow — never `*ngIf` / `*ngFor`.
- Every `setInterval` must have a `clearInterval` on job completion.

**Chain layer:**
- `generate()` and `stream()` inject builder/principles context automatically.
- `rewrite()` and `stream_generate()` are caller-driven — no injection.
- `ProviderError(msg, status)` is the only exception type to catch from chain calls.

## Docker

Local dev: `docker compose up -d` (uses override — ports 8095 web, 8096 landing).
API container mounts `~/.claude` and `~/.claude-openclaw` for CLI credentials.
Rebuild API: `docker compose build api && docker compose up -d api`.
Logs: `docker compose logs -f api`.
