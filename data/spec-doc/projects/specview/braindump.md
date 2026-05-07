# Braindump: specview

## What it is

Specview is a self-hosted spec generation tool and its own Claude Code plugin system. Users paste a braindump; an AI chain generates analysis, epic, architecture, timeline, and implementation guide. It also ships a Claude Code plugin (`plugin/`) that encodes Flask/Angular/chain conventions once so every dev session auto-loads the right reference files and skill/agent routing.

Stack: Flask API (Python 3.11) + Angular 17 SPA (signals, no NgRx) + static nginx landing page. Deployed via Docker Compose on Coolify VPS. AI runs exclusively through `CHAIN_PROVIDER=cli` — the Claude CLI routed through an agent named `chain-agent`.

## The problem it solves

Two problems in one repo. First: braindump → structured spec set is slow and context-heavy to do manually. Specview automates the pipeline via a `bootstrap-project` API call that produces the full spec folder. Second: every dev session on specview itself risks convention drift (wrong Flask pattern, wrong Angular state approach, wrong chain adapter import). The plugin eliminates re-establishing context by encoding conventions in `references/*.md` and routing all work through skill and agent dispatch.

## Current state

Live in production on VPS. Flask API on port 8095, Angular SPA and nginx landing co-deployed. Local dev via `docker compose up -d` with override (port 8095 web, 8096 landing). API container mounts `~/.claude` and `~/.claude-openclaw` for CLI credentials. Plugin is fully wired in `.claude/` with 7 skills and 4 agents.

## Key decisions made

- **CHAIN_PROVIDER=cli always** — never SDK in Docker. The container cannot reach Anthropic directly; all AI calls route through the CLI provider, which optionally dispatches to `chain-agent`.
- **No BehaviorSubject, no Observable for local state** — Angular is signals-only. `signal<T>()` for state, `computed()` for derivations, `@if`/`@for` control flow, never `*ngIf`/`*ngFor`.
- **Adapter boundary enforced structurally** — feature modules import only from `chain/adapter.py`, never from `providers/*`. Pinned by `test_structural.py`.
- **Service functions own transaction boundaries** — `session.commit()` never in route handlers. Blueprints registered with prefix `/api/{name}`.
- **All AI routes behind `@require_auth` + `@check_usage_limit`** — no exceptions.
- **Plugin references are the single source of truth** — convention rules live once in `plugin/references/*.md`. Agents and skills cite them; no inline duplication.
- **Never push to master directly** — always PR, CI (pytest) must pass first.
- **Projects are folders of markdown files** — no database for spec storage; `data/spec-doc/projects/{slug}/` on disk.

## Plugin architecture

7 skills: `dev-build`, `dev-test`, `dev-migrate`, `dev-review`, `spec-pipeline`, `impl-guide`, `exec-guide`. 4 agents: `chain-agent` (AI workflow layer), `spec-backend` (Flask specialist), `spec-frontend` (Angular specialist), `chain-developer` (cross-layer coordinator). The `spec-pipeline` skill calls the bootstrap API to generate the full spec set from a braindump. `impl-guide` turns epic + architecture into a high-level implementation guide. `exec-guide` dispatches tasks from the implementation guide to specialist agents.

`dev-review` fans out to all three specialist agents in parallel. Agents auto-load their reference files at dispatch time — no manual context injection.

## Open questions

- Whether to extract `server.js` (legacy Express path) fully in favor of Flask, or keep it as a dev-only utility.
- Whether to modularize `api/modules/ai/` further as the number of AI workflow types grows.
- Deployment automation: currently manual `git pull + docker compose build` on VPS; no CI-triggered deploy.

## Next steps

- Run `spec-pipeline` on any new feature braindump to generate the full spec set before writing any code.
- Use `exec-guide` to dispatch implementation tasks to specialist agents rather than implementing directly.
- Add any new convention rules to `plugin/references/*.md` before they get copy-pasted elsewhere.
- Smoke test locally (rebuild + verify in browser) before pushing to master.
