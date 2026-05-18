# Implementation Guide: Specview

## Overview
Specview ships a Flask + Angular application that converts braindumps into structured spec folders, alongside a Claude Code plugin that encodes Flask/Angular/chain conventions. The six tasks sequence from foundation upward: plugin references baseline (1) is the single source of truth that everything cites; the chain adapter (2) creates the AI-call boundary; the bootstrap pipeline API (3) wires markdown-on-disk spec generation; the Angular intake/viewer (4) and skill/agent dispatch surface (5) can run in parallel once their dependencies land; finally, Docker Compose deploy (6) binds all three services for local and Coolify environments.

## Shared Pre-flight
- Confirm Python 3.11 and Node 20+ are available; install backend deps from `api/requirements.txt` and frontend deps via `cd web-ng && npm install`.
- Verify `data/spec-doc/projects/` exists at repo root and is writable; create it if missing as the markdown-on-disk root for all generated specs.
- Ensure `plugin/.claude-plugin/plugin.json` exists so Claude Code auto-loads skills, agents, and references on session start.
- Set `CHAIN_PROVIDER=cli` and `CHAIN_AGENT=chain-agent` in `.env` for local dev; Docker will inherit these.
- Mount `~/.claude-openclaw` and provide `CLAUDE_CREDENTIALS_JSON` so the CLI subprocess authenticates without baked-in secrets.
- Run `pytest api/tests/test_structural.py` before any refactor that touches `modules/ai/` or `modules/runtime/chain/` to catch adapter-boundary drift.
- Run `ng build --configuration production` before every frontend commit to surface template + type drift early.
- Branch from master per change; direct master pushes are forbidden — every change lands via PR with green pytest.

---

## Task 1: Plugin references baseline  [Effort: 2 days]

### What
Establish `plugin/references/*.md` as the single source of truth for Flask, Angular, and chain conventions. Every skill and agent must cite these files rather than duplicating rules inline, so this task is the upstream dependency for all routing.

### Files
- **Create**: `plugin/references/flask-conventions.md` — Blueprint shape, `/api/{name}` prefix rule, `session.commit()` in services-only, decorator stacking order.
- **Create**: `plugin/references/angular-conventions.md` — signals-only state, `@if`/`@for` control flow, one-component-per-file, named exports, 200-line cap.
- **Create**: `plugin/references/chain-conventions.md` — adapter boundary rule, `CHAIN_PROVIDER` switch, `chain-agent` routing shape, structural test invariant.
- **Create**: `plugin/.claude-plugin/plugin.json` — plugin manifest declaring skills, agents, and references locations if not already present.
- **Modify**: existing `plugin/skills/*.md` and `plugin/agents/*.md` if any duplicate convention text exists — replace with citation links to the references.

### Steps
1. Draft `flask-conventions.md` covering the route → service → workflow boundary, the `@require_auth` + `@check_usage_limit` stacking requirement on every AI route, and the `/api/{name}` blueprint prefix rule.
2. Draft `angular-conventions.md` enumerating the signals-only mandate (`signal<T>()`, `computed()`), the prohibited primitives (`BehaviorSubject`, `Observable` for local state, `*ngIf`, `*ngFor`), and the file structure rules (one component per file, named exports, under 200 lines).
3. Draft `chain-conventions.md` documenting the adapter as the only AI-call boundary, the CLI-only provider stance in Docker, the `chain-agent` routing pattern, and the structural test invariant that pins the rule.
4. Audit any existing `plugin/skills/*.md` and `plugin/agents/*.md` files for inline convention text using grep; replace duplications with links pointing at the appropriate reference file.
5. Verify the plugin manifest at `plugin/.claude-plugin/plugin.json` advertises the references directory so Claude Code surfaces them on session start.

### Verify
- Run `grep -r "BehaviorSubject\|signal<" plugin/skills plugin/agents` to confirm no skill or agent duplicates Angular state rules inline.
- Run `grep -r "providers/" plugin/skills plugin/agents` to confirm no skill or agent inline-duplicates the chain adapter rule.
- Open each reference file and confirm it stands alone as authoritative (no "see also" loops back into a skill).
- Confirm `plugin/.claude-plugin/plugin.json` validates and the references directory is listed.

---

## Task 2: Chain adapter + CLI provider wiring  [Effort: 2 days]

### What
Build `modules/runtime/chain/adapter.py` as the single AI-call boundary for the entire app, with a CLI provider that subprocesses `claude -p` (optionally `claude --agent chain-agent -p` when `CHAIN_AGENT` is set) and a mock provider for tests. A structural test pins the rule that no module under `modules/ai/` may import from `chain/providers/*`.

### Files
- **Create**: `api/modules/runtime/chain/adapter.py` — exports `generate()`, `stream()`, `rewrite()`, `stream_generate()`; selects provider via `CHAIN_PROVIDER`.
- **Create**: `api/modules/runtime/chain/providers/cli.py` — subprocess wrapper around `claude -p`; honours `CHAIN_AGENT`.
- **Create**: `api/modules/runtime/chain/providers/mock.py` — deterministic stub for tests.
- **Create**: `api/tests/test_structural.py` — fails CI on any `modules/ai/*` import from `chain/providers/*`.
- **Create**: `api/tests/test_chain_adapter.py` — exercises the adapter against the mock provider.
- **Modify**: `api/.env.example` — document `CHAIN_PROVIDER=cli` and `CHAIN_AGENT=chain-agent` defaults.

### Steps
1. Define the adapter API in `adapter.py` with four functions; each dispatches to a provider module selected by reading `CHAIN_PROVIDER` from the environment at call time, defaulting to `cli`.
2. Implement `providers/cli.py` to spawn `claude -p` via subprocess, reading prompt input from stdin and capturing stdout; when `CHAIN_AGENT` is set, prepend `--agent <value>` to the argument list.
3. Implement `providers/mock.py` to return canned responses keyed by the prompt prefix so tests assert against deterministic output.
4. Write `tests/test_structural.py` to walk `modules/ai/` and assert no Python file imports any name from `modules.runtime.chain.providers`; only `modules.runtime.chain.adapter` is permitted.
5. Write `tests/test_chain_adapter.py` covering all four adapter functions against the mock provider, including environment-switch behaviour for `CHAIN_PROVIDER`.
6. Document the env-var defaults in `.env.example` so onboarding picks up CLI-only configuration.

### Verify
- Run `pytest api/tests/test_structural.py` and confirm it passes against current code; intentionally add a forbidden import in a scratch file to confirm the test fails.
- Run `pytest api/tests/test_chain_adapter.py` and confirm all adapter entrypoints exercise the mock provider correctly.
- Run `CHAIN_PROVIDER=cli python -c "from modules.runtime.chain.adapter import generate; print(generate('ping'))"` inside the dev container to confirm the CLI subprocess shells out and returns output.
- Run `grep -r "from modules.runtime.chain.providers" api/modules/ai` and confirm zero matches.

---

## Task 3: Bootstrap pipeline API + spec storage  [Effort: 3 days]

### What
Wire the `bootstrap-project` async chain that turns a braindump into `analysis.md`, `epic.md`, `architecture.md`, `timeline.md`, and `implementation-guide.md` under `data/spec-doc/projects/{slug}/`. Returns 202 + `job_id` immediately, runs the four-step chain in a daemon thread, and exposes a polling status endpoint.

### Files
- **Create**: `api/modules/ai/workflows/spec_gen/bootstrap.py` — four-step chain orchestration calling the adapter; writes markdown files via the data layer.
- **Create**: `api/modules/ai/routes/spec_gen.py` — `POST /api/spec-gen/bootstrap` and `GET /api/spec-gen/status/{job_id}`.
- **Create**: `api/modules/ai/services/job_state.py` — module-level dict + `threading.Lock`; exposes `start()`, `snapshot(job_id)`, `mark_done()`.
- **Create**: `api/modules/data/projects.py` — slug normalization, directory creation, markdown read/write helpers.
- **Create**: `api/modules/data/context_files.py` — `read_context(path)` returning empty string for missing files.
- **Create**: `api/modules/quality/lint.py` — `lint_task_guide()` pre-write gate for malformed sections, missing cross-references, code blocks outside implementation guides.
- **Create**: `api/openapi.yaml` — contract for `/api/spec-gen/*` endpoints.
- **Create**: `api/tests/test_bootstrap_pipeline.py` — async pipeline test using mock provider.
- **Modify**: `api/app.py` — register the new blueprint with `/api/spec-gen` prefix.

### Steps
1. Implement `bootstrap.py` as four explicit `adapter.generate()` calls (analysis → epic → architecture → timeline → implementation-guide); each step's output feeds the next prompt, and all five markdown files are written via `modules/data/projects.py`.
2. Implement `job_state.py` with a module-level dict guarded by `threading.Lock`; `start(job_id)` initializes `{running: True, done: False}`, `snapshot(job_id)` returns the current state, `mark_done(job_id, files)` flips flags and stores file paths.
3. Implement `routes/spec_gen.py` with two endpoints: `POST /api/spec-gen/bootstrap` validates the braindump payload, generates a slug, calls `start(job_id)`, spawns a `daemon=True` thread running `bootstrap()`, returns 202 + `{job_id, slug}`; `GET /api/spec-gen/status/{job_id}` returns `snapshot(job_id)`.
4. Stack `@require_auth` + `@check_usage_limit` on both routes; routes never call `session.commit()` — that lives in service helpers in `modules/data/projects.py`.
5. Implement `modules/quality/lint.py` to scan generated markdown for content-routing violations (status words outside timeline, code blocks outside implementation guides) and raise before the file reaches disk.
6. Author `openapi.yaml` covering request/response shape, status codes (202, 401, 429), and the polling contract; routes implement this contract verbatim.
7. Write `tests/test_bootstrap_pipeline.py` that POSTs a braindump under the mock provider, polls status until `done`, and asserts all five expected files exist on disk under `data/spec-doc/projects/{slug}/`.
8. Register the blueprint in `api/app.py` with the `/api/spec-gen` prefix.

### Verify
- Run `pytest api/tests/test_bootstrap_pipeline.py` and confirm the full async cycle completes against the mock provider.
- Run `curl -X POST http://localhost:3101/api/spec-gen/bootstrap` without an auth header and confirm 401; with an exhausted-usage user, confirm 429.
- POST a braindump with a valid token and poll `/api/spec-gen/status/{job_id}` until `done: true`; confirm all five markdown files appear under `data/spec-doc/projects/{slug}/`.
- Run `pytest api/tests/test_structural.py` to confirm the new workflow modules respect the adapter boundary.

---

## Task 4: Angular intake + spec viewer (signals)  [Effort: 3 days]

### What
Build the signals-only Angular SPA: a braindump intake form that posts to `/api/spec-gen/bootstrap`, polls status until done, and a spec viewer that renders the generated markdown files. State management is `signal<T>()` + `computed()`; templates use `@if` and `@for` exclusively.

### Files
- **Create**: `web-ng/src/app/features/intake/intake.component.ts` — braindump form, signal-driven submit + polling state.
- **Create**: `web-ng/src/app/features/intake/intake.component.html` — `@if`/`@for` template; no `*ngIf` or `*ngFor`.
- **Create**: `web-ng/src/app/features/spec-viewer/spec-viewer.component.ts` — fetches and renders project markdown files.
- **Create**: `web-ng/src/app/features/spec-viewer/spec-viewer.component.html` — sectioned markdown render via `@for`.
- **Create**: `web-ng/src/app/features/projects-list/projects-list.component.ts` — lists projects from `/api/stats/*`.
- **Create**: `web-ng/src/app/services/spec-api.service.ts` — typed HTTP client for spec-gen endpoints; observables only at the HTTP boundary.
- **Create**: `web-ng/src/app/services/markdown.service.ts` — markdown → safe HTML renderer.
- **Modify**: `web-ng/src/app/app.routes.ts` — register intake, spec-viewer, and projects-list routes.

### Steps
1. Implement `intake.component.ts` with `braindump = signal('')`, `submitting = signal(false)`, `jobId = signal<string|null>(null)`, and `status = signal<Status|null>(null)`; submit calls `specApi.bootstrap()` and starts a polling effect that calls `specApi.status()` on an interval until `done`.
2. Author `intake.component.html` using a `<form>` bound to the signal, an `@if (submitting())` block for the loader, and an `@if (status()?.done)` block for the success view linking to the spec viewer.
3. Implement `spec-viewer.component.ts` that resolves the slug from the route, fetches each markdown file via `specApi.readFile()`, stores them in `files = signal<Record<string,string>>({})`, and exposes a `computed()` ordering by document type.
4. Author `spec-viewer.component.html` with `@for (file of orderedFiles(); track file.name)` rendering each file via the markdown service into a sectioned layout.
5. Implement `projects-list.component.ts` and template using the same signals pattern; lists projects with their generated file counts from `/api/stats/*`.
6. Implement `services/spec-api.service.ts` as a typed HTTP client; observables exist only at the HTTP boundary — components convert results into signals immediately on subscribe.
7. Implement `services/markdown.service.ts` to render markdown to sanitized HTML for safe binding.
8. Register the three routes in `app.routes.ts` with lazy imports to keep initial bundle small.

### Verify
- Run `ng build --configuration production` from `web-ng/` and confirm zero errors.
- Run `grep -rE "BehaviorSubject|\*ngIf|\*ngFor|Observable<.*>\s*=" web-ng/src/app` and confirm zero matches outside `services/spec-api.service.ts`.
- Start the dev server with `ng serve`, submit a braindump in the browser, and confirm intake polls and transitions to the spec viewer with all five files rendered.
- Confirm projects-list renders existing slugs from `data/spec-doc/projects/`.

---

## Task 5: Skill/agent dispatch surface  [Effort: 2 days]

### What
Wire the 9 skills (`brainstorm`, `dev-build`, `dev-test`, `dev-migrate`, `dev-review`, `spec-pipeline`, `impl-guide`, `exec-guide`, `triage-projects`) and 4 agents (`chain-agent`, `spec-backend`, `spec-frontend`, `chain-developer`) so each routes work via reference citations rather than inline rules. `dev-review` fans out to the three specialist agents in parallel, and `exec-guide` dispatches each implementation-guide task to the specialist whose reference owns it.

### Files
- **Create**: `plugin/skills/spec-pipeline.md` — orchestrates the bootstrap chain end-to-end.
- **Create**: `plugin/skills/impl-guide.md` — generates high-level guide from epic + architecture.
- **Create**: `plugin/skills/exec-guide.md` — dispatches each task to the right specialist agent.
- **Create**: `plugin/skills/triage-projects.md` — surfaces status across `data/spec-doc/projects/`.
- **Create**: `plugin/skills/brainstorm.md` — pre-spec ideation flow.
- **Create**: `plugin/skills/dev-build.md`, `plugin/skills/dev-test.md`, `plugin/skills/dev-migrate.md`, `plugin/skills/dev-review.md` — dev-lane skills.
- **Create**: `plugin/agents/chain-agent.md` — workflow layer for the CLI provider.
- **Create**: `plugin/agents/spec-backend.md` — Flask specialist; cites `flask-conventions.md` + `chain-conventions.md`.
- **Create**: `plugin/agents/spec-frontend.md` — Angular specialist; cites `angular-conventions.md`.
- **Create**: `plugin/agents/chain-developer.md` — cross-layer coordinator; cites all three references.
- **Create**: `tools/audit_references.sh` — grep audit script that fails when a skill/agent inline-duplicates a reference rule.

### Steps
1. Author each skill in `plugin/skills/` so it states its purpose, lists its triggering invocations, and cites the relevant `plugin/references/*.md` files for any convention rule rather than restating them.
2. Author `dev-review.md` to declare a parallel fan-out to `spec-backend`, `spec-frontend`, and `chain-developer`; the skill returns three reports verbatim (the open question on merging is deferred per analysis).
3. Author `exec-guide.md` so it reads the implementation guide, parses task headers, and dispatches each task to the agent whose reference owns its files (Flask paths → `spec-backend`, Angular paths → `spec-frontend`, chain paths → `chain-developer`).
4. Author each agent in `plugin/agents/` with explicit `references:` frontmatter listing the markdown files it loads at dispatch; agents do not embed convention text.
5. Author `chain-agent.md` as the CLI provider's workflow agent — the only agent invoked from production code via `claude --agent chain-agent -p`; it owns multi-turn conversation shape for chained generations.
6. Write `tools/audit_references.sh` to grep for known convention phrases (e.g., `signal<`, `BehaviorSubject`, `providers/`) inside `plugin/skills/` and `plugin/agents/`; exit non-zero on any match, since those phrases must live only in references.
7. Add the audit script to the pytest gate or a CI hook so convention drift surfaces on every PR.

### Verify
- Run `bash tools/audit_references.sh` and confirm exit 0 against the current skill/agent set.
- Open `plugin/skills/dev-review.md` and confirm it explicitly enumerates parallel fan-out to all three specialist agents.
- Trigger `dev-review` in a Claude Code session and confirm three agents return reports.
- Trigger `exec-guide` against this implementation guide and confirm task 1 routes to `chain-developer`, task 4 routes to `spec-frontend`, etc.

---

## Task 6: Docker Compose + Coolify deploy  [Effort: 1 day]

### What
Wire `docker-compose.yml` so `api` (Flask + gunicorn on internal port 3101), `web` (nginx serving the Angular build on local 8095), and `landing` (nginx:alpine on local 8096) come up together. Local dev uses fixed ports; the Coolify VPS override uses Traefik labels and no fixed host ports, mounting `~/.claude-openclaw` and reading `CLAUDE_CREDENTIALS_JSON` for the CLI subprocess.

### Files
- **Create**: `docker-compose.yml` — three-service base file with shared network and env-var passthrough.
- **Create**: `docker-compose.override.yml` — local dev: fixed ports 3101/8095/8096.
- **Create**: `docker-compose.coolify.yml` — Coolify-specific: Traefik labels, no fixed host ports.
- **Create**: `api/Dockerfile` — Python 3.11 base, gunicorn entrypoint with `--workers 1 --threads 4 --worker-class gthread`.
- **Create**: `web-ng/Dockerfile` — multi-stage; `ng build --configuration production` then nginx serve.
- **Create**: `landing/Dockerfile` — `nginx:alpine` serving static files.
- **Create**: `api/nginx.conf`, `landing/nginx.conf` — reverse-proxy and static-serve configs.
- **Create**: `.dockerignore` files for each build context.

### Steps
1. Author `api/Dockerfile` on a Python 3.11 slim base, install requirements, copy source, and set the entrypoint to `gunicorn --workers 1 --threads 4 --worker-class gthread --bind 0.0.0.0:3101 app:app` (single worker is required because job state is a module-level dict).
2. Author `web-ng/Dockerfile` as multi-stage: stage 1 runs `npm ci && ng build --configuration production`, stage 2 copies `dist/` into `nginx:alpine`.
3. Author `landing/Dockerfile` based on `nginx:alpine` copying static assets into the nginx html root.
4. Author `docker-compose.yml` as the base file with three services on a shared bridge network, env-var passthrough for `CHAIN_PROVIDER`, `CHAIN_AGENT`, and `CLAUDE_CREDENTIALS_JSON`, and a volume mount for `~/.claude-openclaw` on the api service.
5. Author `docker-compose.override.yml` mapping host ports 3101 → api, 8095 → web, 8096 → landing for local development.
6. Author `docker-compose.coolify.yml` with Traefik labels routing by hostname instead of fixed ports, suitable for the VPS environment.
7. Document in repo readme (or release notes) that deploy is manual via `git pull && docker compose -f docker-compose.yml -f docker-compose.coolify.yml build && docker compose up -d` per the open-question decision to defer auto-deploy.

### Verify
- Run `docker compose up -d` locally and confirm `curl http://localhost:3101/api/spec-gen/status/probe` returns 401 (auth required), `curl http://localhost:8095` returns the Angular index, and `curl http://localhost:8096` returns the landing page.
- Run `docker compose exec api python -c "import os; print(os.environ['CHAIN_PROVIDER'])"` and confirm output is `cli`.
- Run `docker compose exec api claude --version` to confirm the CLI binary and credential mount work inside the container.
- Deploy to the Coolify VPS using the override file and confirm Traefik routes both the SPA hostname and the landing hostname without fixed ports clashing.