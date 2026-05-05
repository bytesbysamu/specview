# Engineering Principles — Sam's Projects

Non-negotiable across all projects. When a brain dump contradicts a principle, the analysis step must flag it.

## P1 — Adapter Boundary
All external service calls (AI, DB, storage, HTTP) go through a single adapter module.
No feature code imports a provider directly. The adapter is the only file that knows which provider is active.
- spec-doc: `modules/chain/adapter.py`
- OpenClaw plugins: wrap external calls in a dedicated skill or tool wrapper

## P2 — Thin HTTP Layer
Route handlers contain no business logic. Handlers: validate input → call service → return response.
- Flask: `routes.py` handles HTTP only; `service.py` holds pure Python logic
- OpenClaw: skill files describe tool invocations; no inline logic

## P3 — Async 202 + Polling for Long Operations
Any operation > 30s returns 202 immediately with a job identifier.
A background thread does the work. A status endpoint lets the client poll until `done: true`.
No HTTP connection held open. No Redis — in-process state keyed by job/project id.

## P4 — No Speculative Abstractions
Build for the one concrete case that exists now. No generic runners for one consumer.
No base classes for one subclass. No registries for one item.
Three similar lines of code is better than a premature abstraction.

## P5 — OpenAPI-First (spec-doc)
`openapi.yaml` is the contract. DTOs are generated from it. Never hand-edit generated files.
Routes implement the contract — not the other way around.

## P6 — OpenClaw Plugin Principles
- Skills first: start with `SKILL.md` files (no build step, iterate fast)
- Graduate to `openclaw.plugin.json` package only when skills hit real limits
- References are the single source of truth — no rules duplicated inline in agents/skills
- Agents are declarative descriptions, not imperative code
- Context files (`MEMORY.md`, `USER.md`, `TOOLS.md`) are loaded every session — keep them current
- Boot hooks fire on session start — keep them cheap (no blocking I/O)
- Channel-aware: skills must adjust output format per channel (Telegram ≠ web UI)

## P7 — File Size & Structure
- Files under 200 lines (hard target, not a guideline)
- Named exports only (no default exports in Angular/TS)
- One component per file
- Build verification required before each commit (Angular: `ng build --configuration production`)

## Code Rules
- No direct push to master — always PRs; PRs target master; live is deploy branch
- Daemon threads only (`daemon=True`) — never block server shutdown
- Empty context strings handled gracefully — callers never crash on missing context
- `read_context()` returns `""` for missing files; `PromptBuilder.section()` skips empty content
