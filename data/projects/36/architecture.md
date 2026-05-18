# 🏗️ Solution Architecture: Specview

## Architecture Overview

Specview is two systems sharing one repo: a Flask + Angular app that turns braindumps into spec folders, and a Claude Code plugin that encodes the conventions used to build that app. The mental model is **convention compounding** — every spec the tool generates is also implemented under the conventions the plugin enforces, so the references that route the agent are the same references the generated specs cite. The repo dogfoods itself.

The architectural keystone is the chain adapter. Every AI call — bootstrap pipeline, task generation, rewrites, streaming — exits through `modules/runtime/chain/adapter.py` and only that module knows a provider exists. In the Docker container the only provider wired is `cli`, because the container has no outbound Anthropic access; the CLI subprocess optionally routes through a named `chain-agent` so workflow logic lives in declarative agent files rather than Python. A structural test pins this boundary so a feature module that reaches into `providers/*` fails CI.

The bootstrap pipeline is a four-step chain that runs in a daemon thread and returns 202 immediately with a job id; clients poll a status endpoint until `done: true`. Specs are markdown files on disk under `data/spec-doc/projects/{slug}/` — no database, no queue, no Redis. The Angular SPA is signals-only; control flow is `@if`/`@for`; local state is `signal<T>()` and `computed()`. The plugin half routes every dev action — build, test, review, spec, exec — through skills that cite references rather than inline rules, and `dev-review` fans out to three specialist agents in parallel.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P1 — Adapter Boundary** | All AI calls route through `modules/runtime/chain/adapter.py`. Providers (`cli`, `claude`, `mock`) live behind it; feature code never imports from `providers/*`. Pinned by `test_structural.py`. |
| **P2 — Thin HTTP Layer** | Routes in `modules/ai/routes/` validate, dispatch, return. Workflow logic lives in `modules/ai/workflows/spec_gen/bootstrap.py` and `modules/ai/services/`. Service functions own commit boundaries; routes never call `session.commit()`. |
| **P3 — Async 202 + Polling** | `bootstrap-project` and `generate-task` return 202 + `job_id` immediately. A daemon thread runs the chain. `GET /status/{job_id}` polls until `done`. State is a module-level dict + `threading.Lock` — no Redis. |
| **P4 — No Speculative Abstraction** | Single CLI provider in production; the SDK provider stays out of Docker until a second concrete consumer exists. No generic workflow runner — `bootstrap.py` is one explicit chain. |
| **P5 — OpenAPI-First** | `openapi.yaml` is the contract for `/api/spec-gen/*`, `/api/task-gen/*`, `/api/text/*`, `/api/stats/*`. DTOs are generated; routes implement the contract. |
| **P6 — Plugin References as SSOT** | Flask, Angular, chain rules live once in `plugin/references/*.md`. Agents and skills cite them. A grep audit fails any skill/agent that inline-duplicates a reference rule. |
| **P7 — File Size & Structure** | Files under 200 lines. Named exports only. One Angular component per file. `ng build --configuration production` required before commit. |
| **Auth + Usage Always-On** | Every AI route carries `@require_auth` + `@check_usage_limit`. 401 without auth, 429 over limit — no exceptions, no “internal-only” bypass. |
| **Markdown on Disk** | Specs are folders of `.md` files, not rows. Filesystem is the database; concurrent multi-user editing is explicitly out of scope. |

## Component Design

### Chain Adapter (`modules/runtime/chain/`)
**Purpose**: Single AI call boundary for the entire app. The adapter exposes `generate()`, `stream()`, `rewrite()`, `stream_generate()` and selects a provider via `CHAIN_PROVIDER`. In Docker, `cli` is the only path — a `claude -p` subprocess, optionally `claude --agent chain-agent -p` when `CHAIN_AGENT` is set. Routing through an agent moves multi-turn workflow shape out of Python and into declarative agent files. The `mock` provider exists solely for tests. The structural test asserts that no module under `modules/ai/` imports from `chain/providers/*`.

### Bootstrap Pipeline (`modules/ai/workflows/spec_gen/bootstrap.py`)
**Purpose**: Four-step chain that takes a braindump and writes `analysis.md`, `epic.md`, `architecture.md`, `timeline.md`, and `implementation-guide.md` into `data/spec-doc/projects/{slug}/`. Each step calls the adapter; outputs feed the next step's prompt. Runs in a `daemon=True` thread so server shutdown is never blocked. Job state lives in a module-level dict; `snapshot(job_id)` returns `{ running, done, error?, files? }`.

### Spec Generation Routes (`modules/ai/routes/spec_gen.py`, `task_gen.py`, `text.py`, `stats.py`)
**Purpose**: Thin HTTP surface. `POST /api/spec-gen/bootstrap` validates the braindump, kicks off the pipeline, returns 202 + job id. `GET /api/spec-gen/status/{job_id}` reports snapshot. `task_gen` mirrors the same async shape for per-task implementation guides. `text.py` handles inline rewrites; `stats.py` exposes per-project file metadata. All four blueprints carry `@require_auth` + `@check_usage_limit`.

### Project Storage (`modules/data/`)
**Purpose**: CRUD over `data/spec-doc/projects/{slug}/`. A project is a folder containing `project.json` + named markdown files. The context file service exposes `read_context(path)` returning `""` for missing files so prompt builders never crash on absent context. There is no database; slug uniqueness is enforced by directory existence.

### Quality Gate (`modules/quality/`)
**Purpose**: `lint_task_guide()` runs before any generated guide is written to disk. Catches malformed sections, missing cross-references, and content-routing violations (status words outside timeline, code blocks outside implementation guides). A pre-write gate, not a post-hoc check — bad output never reaches disk.

### Auth Layer (`modules/auth/`)
**Purpose**: `@require_auth` decodes JWT and attaches user identity; `@check_usage_limit` increments per-user counters and returns 429 over threshold. Decorators stack on every AI route. Auth state never leaks into service or workflow modules.

### Angular SPA (`web-ng/src/app/`)
**Purpose**: Signals-only intake and viewer. Braindump form posts to bootstrap, then polls status. Spec viewer reads markdown files via API and renders them. State management is `signal<T>()` + `computed()`; templates use `@if`/`@for`. Zero `BehaviorSubject`, zero `Observable` for local state, zero `*ngIf`/`*ngFor` — enforced by grep audit. Components are one-per-file, named exports, under 200 lines.

### Static Landing (`landing/`)
**Purpose**: Marketing page on `nginx:alpine`. Independent of the API container so it can stay up while the app rebuilds. Local port 8096; on Coolify, Traefik routes by hostname.

### Plugin Surface (`plugin/`)
**Purpose**: 9 skills + 4 agents that route every dev session through references.

- **References** (`plugin/references/`): `flask-conventions.md`, `angular-conventions.md`, `chain-conventions.md` — single source of truth. Every skill/agent cites them; no inline duplication.
- **Skills** (`plugin/skills/`):
  - *Spec lane*: `spec-pipeline` (orchestrates bootstrap), `impl-guide` (epic + architecture → high-level guide), `exec-guide` (dispatch tasks to specialists), `triage-projects` (status across projects), `brainstorm` (pre-spec ideation).
  - *Dev lane*: `dev-build`, `dev-test`, `dev-migrate`, `dev-review`.
- **Agents** (`plugin/agents/`):
  - `chain-agent` — workflow layer for the CLI provider; the only agent invoked from production code.
  - `spec-backend` — Flask specialist; loads `flask-conventions.md` + `chain-conventions.md`.
  - `spec-frontend` — Angular specialist; loads `angular-conventions.md`.
  - `chain-developer` — cross-layer coordinator; loads all three references.
- **Dispatch shape**: `dev-review` fans out to all three specialist agents in parallel. `exec-guide` reads the implementation guide and routes each task to the specialist whose reference owns it.

### Deployment Topology
**Purpose**: One Compose file, three services. `api` (Flask + gunicorn, port 3101 internal), `web` (nginx serving Angular build, port 8095 local), `landing` (nginx:alpine, port 8096 local). Local dev exposes fixed ports; Coolify VPS uses Traefik labels and no fixed host ports. The API container mounts `~/.claude-openclaw` and receives `CLAUDE_CREDENTIALS_JSON` so the CLI subprocess can authenticate without baking secrets into the image.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Flask (Python 3.11) | Thin HTTP boundary, Blueprint-per-domain, ~150-line routes. Sam's default for AI service shells. |
| Backend WSGI | gunicorn `--workers 1 --threads 4 --worker-class gthread` | Single worker is required for module-level dict job state. `gthread` lets daemon threads coexist. |
| AI Provider | Claude CLI via `chain-agent` | Container has no outbound Anthropic access; CLI subprocess is the only viable path. Agent routing keeps workflow shape declarative. |
| Adapter | `modules/runtime/chain/adapter.py` | Single boundary; provider switch by env var. Structural test pins the rule. |
| Frontend | Angular 19, signals-only | Modern Angular control flow + reactivity without NgRx ceremony. Non-negotiable per builder principles. |
| Frontend Build | `ng build --configuration production` | Required pre-commit gate; catches template + type drift early. |
| Storage | Markdown files on disk | Specs are documents, not rows. No DB removes a whole class of failure modes. Multi-user concurrent edit is out of scope. |
| Job State | Module-level dict + `threading.Lock` | In-process is fine for single-consumer async; no Redis. Couples to single-worker gunicorn. |
| Async Pattern | 202 + `job_id` + polling | Long generations can run minutes; no held HTTP connections. Same shape Sam uses across projects. |
| Auth | JWT + `@require_auth` decorator | Stateless; works for any client. Pairs with `@check_usage_limit` for billing-adjacent enforcement. |
| Landing | `nginx:alpine` static | No build coupling to the app; survives API rebuilds. |
| Deploy (local) | `docker compose up -d` with override | Same image as prod; override only adjusts ports + mounts. |
| Deploy (prod) | Coolify on VPS, Traefik routing | Self-hosted, zero per-seat cost, Sam controls the prompt chain end-to-end. |
| CI | pytest on PR | Structural test + grep audits gate convention drift. No direct master pushes. |
| Plugin Format | Claude Code plugin (`.claude/`) | Already wired; skills and agents auto-load on session start. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **CLI provider only in Docker, no SDK path** | Container has no outbound Anthropic access. The CLI subprocess is the contract; SDK code in production paths would be dead weight. | Lose SDK ergonomics (token streaming, structured tool use). Acceptable because `chain-agent` provides workflow shape and the CLI's 3600s timeout is sufficient for chained generations. |
| **Workflow logic in `chain-agent`, not Python** | Routing through `claude --agent chain-agent -p` keeps multi-turn shape declarative. Iteration is editing markdown, not Python. | Two places to look when debugging a chain (Python step + agent file). Mitigated by keeping `bootstrap.py` to four explicit steps and pushing only conversation shape into the agent. |
| **Markdown files on disk, no database** | Specs are documents users read and edit; rows would be a regression. Filesystem is observable, diffable, and Coolify-backupable. | No multi-user concurrent edit, no row-level history, no full-text search server-side. All deferred until a real second user exists. |
| **Module-level dict for job state, single gunicorn worker** | In-process is fine for single-consumer async per builder principles. Avoids Redis entirely. | Cannot scale to multi-worker or multi-replica. If concurrency demand appears, the boundary to swap is the snapshot module — not the whole stack. |
| **Plugin references as the single source of truth** | Convention rules drift the moment they're inline-duplicated. Centralising them in `plugin/references/*.md` means one edit propagates to every skill and agent. | A skill/agent file alone doesn't read self-contained — readers must follow the citation. Acceptable because the agent loads the reference automatically at dispatch. |
| **Signals-only Angular, no `BehaviorSubject` / `Observable` for local state** | Angular 19's primitives subsume RxJS for local state. NgRx is ceremony for a single-consumer SPA. | Loses RxJS operator vocabulary for local flows. Acceptable — async I/O still uses observables at the HTTP boundary; the ban is local state only. |
| **Adapter boundary pinned by `test_structural.py`** | Convention drift is invisible until something breaks. A structural test makes the rule executable. | Adds a CI step that fails on legitimate refactors that move the adapter. Acceptable because moving the adapter is a deliberate architectural event. |
| **`dev-review` fans out to three specialists in parallel** | Backend, frontend, and chain-layer review have orthogonal concerns; serialising them wastes wall time. | Three agent invocations cost more tokens than one merged reviewer. Acceptable because review quality is the bottleneck on PR merge. |
| **Auth + usage gate on every AI route, no internal exceptions** | One missing decorator becomes the production incident. Uniform decoration removes the audit surface. | Internal smoke tests need a service token. Acceptable cost for a one-line auth invariant. |
| **Manual deploy via `git pull + docker compose build`** | Solo developer, low push frequency. CI-triggered auto-deploy adds infra without saving meaningful time. | Risk of staleness between merge and deploy. Open question — revisit if push cadence increases. |
| **No further modularization of `modules/ai/` yet** | Current shape (routes / services / workflows / prompts) is legible at three workflow types. Splitting now is speculative. | If workflow count grows, the directory will need a second axis. Open question; flagged but not blocking. |
| **Bootstrap is one synchronous chain, not an event graph** | Four sequential steps with deterministic dependencies. An event graph would be P4 violation for one consumer. | Cannot rerun a single step in isolation without re-running prior steps' prompts. Acceptable because the whole chain runs in minutes and idempotent re-runs are cheap. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking