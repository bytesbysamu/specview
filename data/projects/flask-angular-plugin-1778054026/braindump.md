# Brain Dump: Claude Code Provider Plugin

> **Date**: 2026-05-05
> **Status**: raw — everything I know, unfiltered
> **Purpose**: a general-purpose Claude Code plugin with two jobs: (1) expose a provider interface the backend chain adapter can call directly — replacing the `cli.py` subprocess — so any Flask backend can use Claude Code as its AI engine; (2) encode the Flask/Angular stack conventions so the AI never needs re-briefing between sessions

---

## How the Backend Uses the Plugin

`providers/cli.py` already calls `claude -p "<prompt>"` as a subprocess. The plugin does NOT replace this mechanism — it enhances it. With the plugin installed and loaded, the backend's CLI calls gain:

- **Agents**: instead of passing a raw system prompt, call a named agent that already has the right conventions loaded. `claude --agent chain-agent -p "<task>"` — the agent reads `chain-conventions.md` before acting.
- **Skills**: the backend can invoke a named skill (`/dev-build`, `/dev-test`) via CLI, the same way a human would, and the skill executes with proper abort conditions.
- **References**: convention files loaded automatically into agent context — the backend never re-sends the full system prompt; the plugin handles it.

**Today** (raw CLI call):
```python
# providers/cli.py
result = subprocess.run(["claude", "-p", system + "\n\n" + prompt], ...)
```

**With the plugin** (agent-routed CLI call):
```python
# providers/cli.py (enhanced)
result = subprocess.run(["claude", "--agent", "chain-agent", "-p", prompt], ...)
```

The `chain-agent` picks up `chain-conventions.md` and `flask-conventions.md` from the plugin's `references/` directory. The system prompt shrinks to just the task; the conventions come from the plugin.

**Plugin structure mirrors financing-plugin exactly:**
```
claude-code-provider-plugin/
  .claude-plugin/
    plugin.json
  agents/
    chain-agent.md       ← handles all backend AI call requests
    spec-backend.md      ← Flask/Python expert (for dev sessions)
    spec-frontend.md     ← Angular 19 expert (for dev sessions)
  skills/
    dev-build/SKILL.md
    dev-test/SKILL.md
    dev-migrate/SKILL.md
    dev-review/SKILL.md
    SKILL_MAP.md
  references/
    chain-conventions.md
    flask-conventions.md
    angular-conventions.md
  hooks/
    hooks.json
    session-start.mjs
```

The `chain-agent` is the primary consumer from the backend. The other agents and skills are for human dev sessions — same plugin, two consumers.

---

## Convention Encoding (Secondary — Dev Sessions)

Every session I start on spec-doc or specview, I spend 10–15 minutes re-establishing context:
- What the module structure looks like
- The chain adapter pattern and why we never import providers directly
- Which SQLModel pattern to use (and not use)
- The Angular 19 signals idiom vs the old RxJS Observable approach
- The Docker Compose dev workflow (never restart executor)
- The Alembic migration rules per project

The financing-plugin solved this for the Java/Spring/Angular world — it baked conventions into agents and skills so Claude never guesses. We need the same thing for the Python/Flask/Angular world.

---

## The Stack

### Backend: spec-doc API

**Language & Framework**
- Python 3.12 (via Gunicorn in Docker)
- Flask Blueprints — one Blueprint per module (registered in `app.py`)
- SQLModel (Pydantic v2 + SQLAlchemy 2) for all ORM models
- Alembic for migrations — separate `version_table` per project (`specview_alembic_version`, `specview_alembic_version`, etc.)
- bcrypt (work-factor 12) + PyJWT HS256 (72h) for auth

**Module structure (9 modules at `/api/modules/`)**
```
modules/
  ai/          ← text operation routes (expand/compress/clarify/rewrite)
  auth/        ← bcrypt+JWT login, decorators, models
  billing/     ← usage/limits (placeholder, growing)
  data/        ← project file loading from /data/projects/
  observability/ ← structlog, request IDs
  quality/     ← linting, coherence checks
  runtime/     ← chain adapter + providers (THE core AI layer)
    chain/
      adapter.py     ← SOLE import point for AI. ELA #1.
      providers/
        claude.py    ← Anthropic SDK (production)
        cli.py       ← Claude CLI subprocess (dev-only)
        mock.py      ← deterministic test double
      context.py     ← with_context(): prepend builder/principles to system
      types.py       ← ChainResult, ChainStep, ChainDefinition
      workflows/     ← chain declarations (SPEC_CHAIN, BOOTSTRAP_CHAIN, etc.)
  usage/       ← token/cost accumulator (_USAGE dict, _PRICING table)
  web_serve/   ← nginx config, static delivery
```

**THE cardinal rule**: feature modules import ONLY from `modules/runtime/chain/adapter.py`. Never from `providers.*` directly. Enforced by `test_structural.py`.

**Chain adapter resolution order**
```
CHAIN_PROVIDER env var (explicit) → use it
ANTHROPIC_API_KEY present → "claude" (SDK)
ANTHROPIC_CLI_KEY present → inject as ANTHROPIC_API_KEY → "claude" (SDK)
otherwise → "cli" (host subprocess, dev-only)
```

**AI call functions in adapter.py**
- `generate(system, prompt, *, builder, principles, model, max_tokens)` → ChainResult
- `rewrite(system, prompt, *, model, max_tokens)` → ChainResult (no context injection)
- `stream(system, prompt, ...)` → Iterator[str]
- `stream_generate(system, prompt, ...)` → Iterator[str] (no context, for workflow AICall steps)

**DEFAULT_MODEL = "claude-sonnet-4-5"**

**Workflow steps (in `runtime/workflows/steps/`)**
- `AICall` — single AI step, `stream=True` supported via `stream_generate`
- `Transform` — pure Python transformation step
- `Conditional` — branch on a condition

**SQLModel conventions**
- `class User(SQLModel, table=True)` for DB tables
- `Optional[str]` for nullable columns
- `Field(default=None)` for optional fields
- No `@property` for computed DB stuff — keep models thin

**Auth pattern**
- `POST /api/auth/login` → bcrypt verify → issue JWT (72h, HS256, `JWT_SECRET` env)
- `@require_auth` decorator → verify JWT → `_load_user(sub)` from DB
- No register route — seed users via Alembic data migration or CLI

**Migration conventions**
- Alembic in `api/migrations/`
- `version_table="specview_alembic_version"` in env.py (isolates from shared Neon DB)
- File naming: `NNNN_description.py` (sequential number prefix)
- Always `upgrade()` + `downgrade()` 
- Data migrations allowed (seed users, backfill columns)

---

### Frontend: specview (Angular 19)

**Stack**
- Angular 19, standalone components ONLY — no NgModules
- TypeScript strict mode
- Signals-first: `signal()`, `computed()`, `effect()` — no RxJS Subjects, no BehaviorSubject
- `marked` for Markdown → HTML rendering
- `DomSanitizer.bypassSecurityTrustHtml()` for rendered HTML
- `HttpClient` with an interceptor that adds the JWT `Authorization: Bearer` header

**Component structure**
```
src/app/
  app.component.ts      ← root component, all state lives here
  app.component.html
  components/
    login/login.component.ts   ← login form
  services/
    auth.service.ts     ← JWT storage (localStorage), isLoggedIn signal
    projects.service.ts ← HTTP calls to /api/projects, /api/projects/:id, /api/context/:key
    ai.service.ts       ← HTTP calls to /api/ai/text/* (expand/compress/clarify/rewrite)
  interceptors/
    auth.interceptor.ts ← adds Authorization header + redirects on 401
```

**Signals idiom**
```typescript
// State
projects = signal<Project[]>([]);
activeSection = signal('all');

// Computed (no side effects)
filteredProjects = computed(() => { ... });

// Effect (side effects — use sparingly, only for subscriptions)
effect(() => {
  if (this.auth.isLoggedIn()) {
    this.loadProjects();
  }
});
```

**NEVER**: `Observable.subscribe()` in components, `ngOnChanges` with complex logic, `@Input()` on root component, `NgModule` imports.

**Template idiom (Angular 19 control flow)**
```html
@if (condition) { ... }
@for (item of list; track item.id) { ... }
```

**HTTP calls**: always `async/await` in the component, `firstValueFrom(http.get(...))` in services.

**Build target**: `ng build --configuration production` → `dist/web-ng/browser/` → served by nginx.

---

### Docker Compose

**Services**: `web` (nginx, serves Angular), `api` (Gunicorn/Flask), `db` (Neon Postgres via env var, not a local container)

**Dev rule**: NEVER `docker compose down` or `docker compose restart`. Use `docker exec` for one-off commands. To rebuild: `docker compose build api && docker compose up -d api`.

**Key env vars**
```
DATABASE_URL        ← Neon Postgres connection string
JWT_SECRET          ← HS256 signing key (64-char hex)
ANTHROPIC_API_KEY   ← production Anthropic key
ANTHROPIC_CLI_KEY   ← dev: OAuth token from macOS keychain, adapter injects as API key
CHAIN_PROVIDER      ← explicit override (claude/cli/mock)
```

---

## What Financing-Plugin Got Right

The financing-plugin structure is the gold standard to copy:

```
financing-plugin-extracted/
  .claude-plugin/
    plugin.json       ← name, description, version, dependencies
    marketplace.json  ← listing info
  agents/
    fin-backend.md    ← Spring/Java expert agent
    fin-frontend.md   ← Angular expert agent
    fin-test-developer.md
  skills/
    dev-build/SKILL.md
    dev-test/SKILL.md
    dev-migration/SKILL.md
    dev-review/SKILL.md
    feature-pipeline/SKILL.md
    feature-prd/SKILL.md
    feature-requirement/SKILL.md
    feature-review/SKILL.md
    bug-fix/SKILL.md
    SKILL_MAP.md
  references/
    spring-conventions.md   ← authoritative rules, read by agents every session
    flyway-conventions.md
    angular-conventions.md
    module-context.md
  hooks/
    hooks.json
    session-start.mjs
```

Key insight from fin-backend.md: **agents read conventions from reference files, never invent rules**. The reference is the source of truth, the agent enforces it.

Key insight from SKILL.md: **skills declare their own abort conditions** (e.g., unknown module → ask user, don't guess).

---

## What Our Plugin Needs

### Agents (3)

**spec-backend** — Flask/Python expert
- Reads `references/flask-conventions.md` for module structure, Blueprint registration, SQLModel patterns
- Reads `references/chain-conventions.md` for adapter rules
- Dispatch: route implementation, SQLModel models, Alembic migrations, auth decorators, chain steps
- Never touches Angular components

**spec-frontend** — Angular 19 expert
- Reads `references/angular-conventions.md` for signals, computed, HttpClient, DomSanitizer
- Dispatch: components, services, interceptors, template syntax
- Never touches Flask routes

**chain-developer** — Chain/workflow specialist
- Reads `references/chain-conventions.md` deeply
- Specializes in `ChainStep`, `ChainDefinition`, `AICall` steps, provider selection
- Dispatch: new workflow declarations, adapter extensions, provider tests

### Skills (5)

**dev-build** — rebuild affected service and verify it starts
- `docker compose build <service> && docker compose up -d <service>`
- Report build errors, never auto-fix

**dev-test** — run pytest suite
- `docker compose exec api pytest api/tests/ -x`
- Report failures, never auto-fix

**dev-migrate** — generate + run Alembic migration
- `docker compose exec api alembic -c api/migrations/alembic.ini revision --autogenerate -m "<name>"`
- Then `upgrade head`
- Verify `specview_alembic_version` table is used

**dev-review** — structural review
- Check: no direct provider imports, no missing `@require_auth`, no NgModule usage in Angular, adapter isolation
- Fan out to `spec-backend` and `spec-frontend` agents

**spec-pipeline** — spec-doc creation pipeline
- Given a topic, scaffold a new spec-doc project: braindump → analysis → epic → architecture → timeline
- Creates files in `/data/projects/<slug>-<timestamp>/`
- Follows the chain primitive project as the gold standard format

### References (3)

**flask-conventions.md**
- Blueprint registration pattern
- SQLModel table/model patterns
- Auth decorator usage
- Alembic version table isolation
- Module import rules (adapter only)

**angular-conventions.md**
- Signals-only state (no RxJS in components)
- Standalone component imports
- HttpClient + interceptor pattern
- Control flow syntax (@if/@for)
- DomSanitizer usage

**chain-conventions.md**
- Adapter as sole import point
- Provider resolution order
- ChainResult shape
- Workflow step composition
- Mock provider for tests (CHAIN_PROVIDER=mock)
- DEFAULT_MODEL and pricing table

### Hooks

**session-start** — inject live context
- Current provider (from `CHAIN_PROVIDER` or resolution logic)
- API health check
- Active migration status

---

## The txs-plugin Reference (from Bubls)

The txs-plugin (transactions plugin for Bubls) encoded:
- Domain event pattern (transaction created → webhook → notification)
- Ionic component conventions (ion-list, ion-item, ion-refresher)
- Capacitor plugin wrappers for native features

Key takeaway: plugins are **domain-aware convention encoders**. But unlike txs-plugin, this plugin has a second job — it must also work as a general-purpose backend provider, not just a convention store for one project.

---

## The sam-plugin Reference

The braindump-sam-plugin (OpenClaw personal plugin) encoded:
- Live tool calls against running services (spec-doc bridge)
- Project registry with paths and URLs
- Telegram-aware response sizing

Key takeaway: the best plugins give agents **live state awareness**, not just static docs. Our `session-start` hook should inject live status (provider, API health, project count) so the agent never has to ask.

---

## What a "second layer backend" means

The plugin is **implementation-layer tooling** — it sits between the human (Sam) and the code. When Sam says "add a new AI text op", the plugin:
1. Routes to `chain-developer` agent (identifies it as a new workflow step)
2. Agent reads `chain-conventions.md` to know the `ChainStep` shape
3. `dev-build` skill verifies it compiles
4. `dev-test` skill verifies structural tests still pass

The "workflow and chains backend" is the runtime module: `adapter.py`, providers, workflow steps. This plugin is specifically equipped to extend that layer without breaking its invariants.

---

## Open Questions

1. Plugin distribution — local only (`~/.claude/plugins/flask-angular-plugin/`) or published to a private registry?
2. Session-start hook — how heavyweight? Full pytest run on boot, or just health-check ping?
3. `dev-migrate` — should it autogenerate from SQLModel diff or require a hand-written migration body?
4. Cross-project use — can this plugin serve both spec-doc and specview from one install, or do we need per-project config?
5. Structural test coverage — do we add an AST test that enforces "no direct provider imports" as part of the plugin's dev-review skill, or rely on existing `test_structural.py`?
