# Thin API Phase 3 — Braindump

## What this is

Phase 3 of the thin API migration. Phase 2 added the generic skill infrastructure (SKILL.md files, generic skill route). Phase 3 is about:

1. Clean, flat, action-named API contract — routes are `/api/brainstorm`, `/api/expand`, etc. No `/text/` or `/ai/` prefix.
2. Frontend becomes dumb — sends data, gets result, knows nothing about prompts or skills
3. All instruction complexity moves to the backend (Python route → skill → SKILL.md → Claude)
4. Angular API client generated from OpenAPI spec — no hand-written HTTP code in the frontend
5. Delete as much Python as possible — migrate all AI routes to skills, including `bootstrap-project` and `generate-epic-guide`

## The problem with the current frontend

`ai.service.ts` today has the brainstorm prompt instructions hardcoded in TypeScript:

```ts
brainstorm(text: string): Promise<TextOperationResponse> {
  return this.rewrite(text, [
    'You are a product thinking partner. Given this raw brain dump, generate a structured brainstorm response...',
    '1. **Key Themes** — ...',
    ...
  ].join('\n'));
}
```

This is wrong. Prompt engineering in TypeScript means:
- Prompts can't be improved without a frontend deploy
- The frontend is aware of AI instructions — it shouldn't be
- All the expand/compress/clarify/simplify/tldr/bullets variants are just `rewrite()` with different instruction strings baked in TypeScript

The fix: each action gets a named flat endpoint. The backend owns the instructions. Frontend sends `{ text }` and gets `{ text, latencyMs }`.

## Current API surface (frontend perspective)

### What the frontend actually calls today

**ai.service.ts:**
- `POST /api/ai/text/rewrite` — used for rewrite, expand, compress, clarify, simplify, tldr, bullets, brainstorm, styleAs (all same endpoint, different instruction strings)
- `POST /api/ai/text/generate` — generic text generation with `{ prompt, tone }`

**projects.service.ts:**
- `POST /api/ai/text/bootstrap-project` — async spec generation (multi-step AI chain)
- `GET /api/ai/text/bootstrap-project/status/<job_id>` — poll bootstrap
- `POST /api/projects/<id>/generate-epic-guide` — async epic guide generation
- `GET /api/projects/<id>/generate-epic-guide/status` — poll epic guide
- `GET /api/projects` — list projects
- `GET /api/projects/<id>` — get project
- `POST /api/projects` — create project
- `PUT /api/projects/<id>/files/<filename>` — save file

## Target API contract — flat, action-named routes

### Text operations (new — replaces the single /rewrite endpoint)

Each action is its own route. No `/text/` or `/ai/` prefix — just the verb. Backend owns all prompt logic.

```
POST /api/brainstorm   { text, question?, context? }  → { text, latencyMs }
POST /api/expand       { text }                        → { text, latencyMs }
POST /api/compress     { text }                        → { text, latencyMs }
POST /api/clarify      { text }                        → { text, latencyMs }
POST /api/simplify     { text }                        → { text, latencyMs }
POST /api/tldr         { text }                        → { text, latencyMs }
POST /api/bullets      { text }                        → { text, latencyMs }
POST /api/rewrite      { text, style }                 → { text, latencyMs }
```

`style` values for `/rewrite`: Concise | Technical | Executive | Narrative | Punchy. Backend maps these to Claude instructions. Frontend doesn't know what those instructions say.

No `/generate` endpoint — it's not used for a clear business action. Remove.

### Angular API client

Generated from `openapi.yaml` using `ng-openapi-gen`. No hand-written HTTP code. `ai.service.ts` is replaced by the generated client. Adding a new action = update openapi.yaml + add SKILL.md + add Flask route. Frontend regenerates automatically.

### Project management (unchanged)

```
GET    /api/projects
POST   /api/projects
GET    /api/projects/<id>
PUT    /api/projects/<id>/files/<filename>
```

### Spec generation (migrate to skills in Phase 3)

`bootstrap-project` and `generate-epic-guide` are multi-step async chains currently implemented in Python. Phase 3 migrates these to skill pipelines — the full chain (analysis → epic → architecture → timeline) runs via SKILL.md + agent, not Python service code. The endpoints stay but the Python behind them becomes a thin job dispatcher.

```
POST   /api/bootstrap          { project_name, braindump }  → { job_id }
GET    /api/bootstrap/<job_id>                               → { done, files, current_step }
POST   /api/projects/<id>/generate-epic-guide               → { job_id }
GET    /api/projects/<id>/generate-epic-guide/status        → { done, filename }
```

## Backend implementation

Each new `/api/text/<action>` route is a thin Python handler:
- Auth check
- Extract `text` from body (+ `style` for rewrite)
- Call the corresponding skill (which calls SKILL.md → Claude)
- Return `{ text, latencyMs }`

The skills already exist or need creating:
- `brainstorm` skill — exists in plugin/skills/
- `rewrite` skill — exists in plugin/skills/
- `expand`, `compress`, `clarify`, `simplify`, `tldr`, `bullets` — may need SKILL.md files created

The Python routes are ~10 lines each. The intelligence lives in SKILL.md.

## What gets deleted

Once the new `/api/<action>` routes are live and the frontend is updated:

### Dead Python routes in text.py
- `POST /api/ai/text/rewrite` — replaced by individual action routes
- `POST /api/ai/text/generate` — removed, no equivalent needed
- `POST /api/ai/text/iterate` — was never called from frontend
- `POST /api/ai/text/lint-braindump` — was never called from frontend
- `POST /api/ai/text/review` — was never called from frontend

### Dead Python files (once routes and bootstrap are migrated)
- `api/modules/ai/services/text_prompts.py` (423 LOC) — all prompt strings
- `api/modules/ai/services/task_gen.py` (537 LOC) — most of it, once bootstrap is a skill pipeline
- `api/modules/ai/workflows/spec_gen/` — Python AI workflow chains replaced by skills
- Their test files

### Dead TypeScript
- `ai.service.ts` — replaced entirely by generated OpenAPI client
- All instruction strings, the `generate()` method, the base URL constants

## What stays

- `bootstrap-project` and `generate-epic-guide` routes (async, complex — Phase 4)
- `quality/` module (still in use by active routes — audit separately)
- `task_gen.py` service (still in use by active routes — audit separately)
- All auth, billing, project CRUD

## What the Angular service looks like after

```typescript
@Injectable({ providedIn: 'root' })
export class AiService {
  private readonly base = '/api/text';
  constructor(private http: HttpClient) {}

  brainstorm(text: string): Promise<TextResponse> {
    return this.post('brainstorm', { text });
  }
  expand(text: string): Promise<TextResponse> {
    return this.post('expand', { text });
  }
  compress(text: string): Promise<TextResponse> {
    return this.post('compress', { text });
  }
  clarify(text: string): Promise<TextResponse> {
    return this.post('clarify', { text });
  }
  simplify(text: string): Promise<TextResponse> {
    return this.post('simplify', { text });
  }
  tldr(text: string): Promise<TextResponse> {
    return this.post('tldr', { text });
  }
  bullets(text: string): Promise<TextResponse> {
    return this.post('bullets', { text });
  }
  rewrite(text: string, style: string): Promise<TextResponse> {
    return this.post('rewrite', { text, style });
  }

  private post(action: string, body: object): Promise<TextResponse> {
    return firstValueFrom(
      this.http.post<TextResponse>(`${this.base}/${action}`, body)
        .pipe(timeout(AI_TIMEOUT_MS))
    );
  }
}
```

No instruction strings. No prompt logic. Each method is ~3 lines.

The `followupBrainstorm()` method in `app.component.ts` currently assembles context and sends a custom rewrite instruction. After Phase 3, this becomes a call to a dedicated `POST /api/text/brainstorm-followup` route, or the brainstorm skill handles the follow-up via the same `/api/text/brainstorm` endpoint with additional context in the body.

## Architectural principle — facade

The API is a facade. The frontend:
- Has zero instruction strings
- Has zero system prompts
- Has zero AI behavior knowledge
- Sends data, receives results

Every AI decision — what the prompt says, how Claude should respond, what context to include — lives in the backend. SKILL.md is the source of truth. Python routes are the facade surface.

This also resolves the followup brainstorm pattern. Currently `app.component.ts` assembles:
```ts
`You are a brainstorming partner. The user wants to explore: "${question}"\n...`
```
That instruction string is eliminated. The endpoint becomes:
```
POST /api/text/brainstorm  { text, question?, context? }  → { text, latencyMs }
```
The SKILL.md decides what to do when `question` is present vs. absent. Frontend sends the data structure, knows nothing about what happens next.

Same principle for style/rewrite: frontend sends `{ text, style: "Concise" }`. Backend maps "Concise" to Claude instructions. Frontend doesn't know what "Concise" means to Claude.

## Sequence

1. Create SKILL.md files for expand, compress, clarify, simplify, tldr, bullets (if they don't exist)
2. Add Python blueprint `/api/text` with 8 route handlers (thin, call skills)
3. Update `ai.service.ts` — new base URL, clean methods, no instruction strings
4. Test end-to-end
5. Delete old `/api/ai/text/rewrite`, `/api/ai/text/generate` routes
6. Delete `text_prompts.py` and its tests
7. Delete dead TypeScript
