# Implementation Guide: Thin API Phase 3

## Overview

Phase 3 flattens the AI text surface to eight action-named routes (`/api/brainstorm`, `/api/expand`, etc.), migrates all prompt logic to SKILL.md files, regenerates the Angular HTTP client from `openapi.yaml`, and deletes 423 LOC of prompt Python. Tasks 1 and 2 are parallel. Tasks 3–5 run in sequence, each depending on the previous.

## Shared Pre-flight

- `CHAIN_PROVIDER=cli` must be set in the API container (already configured).
- Run `cd api && python -m pytest` before starting — baseline must be green.
- After any Python change: `docker compose build api && docker compose up -d api`.
- Angular: `cd web-ng && npm install` before Task 4.
- Auth token for smoke tests: `docker compose exec api python3 -c "from modules.auth.service import create_token; print(create_token(1, 'admin@themesbrand.com'))"`.

---

## Task 1: Six New SKILL.md Files  [Effort: 0.5 day]

### What
Create SKILL.md files for the six text actions that lack them: expand, compress, clarify, simplify, tldr, bullets. `brainstorm` and `rewrite` already exist at `plugin/skills/`. Update brainstorm to support optional followup fields.

### Files
- **Create**: `plugin/skills/expand/SKILL.md`
- **Create**: `plugin/skills/compress/SKILL.md`
- **Create**: `plugin/skills/clarify/SKILL.md`
- **Create**: `plugin/skills/simplify/SKILL.md`
- **Create**: `plugin/skills/tldr/SKILL.md`
- **Create**: `plugin/skills/bullets/SKILL.md`
- **Modify**: `plugin/skills/brainstorm/SKILL.md` — add followup branching on `question` field

### Steps

1. Use `plugin/skills/rewrite/SKILL.md` as the structural template. Each skill receives JSON input and returns `{"text": "..."}` — no preamble, no markdown fences.

2. Write `expand/SKILL.md`: expand the text with more detail, examples, and supporting context. Preserve structure and intent. Do not add opinions or speculative content.

3. Write `compress/SKILL.md`: compress to essential points only. Remove filler, redundancy, and over-explanation. Every distinct idea must survive.

4. Write `clarify/SKILL.md`: rewrite for clarity. Fix ambiguity, tighten logic, improve flow. Do not change meaning or add new content.

5. Write `simplify/SKILL.md`: rewrite in plain language. Remove jargon. Target a non-specialist reader. Preserve all key information.

6. Write `tldr/SKILL.md`: produce a TL;DR as 4–6 tight bullet points. Lead with the most important insight. No commentary or framing text.

7. Write `bullets/SKILL.md`: convert to bullet points grouped by logical sections. Keep every key piece of information.

8. In `plugin/skills/brainstorm/SKILL.md`, update the Input Format to accept optional `question` and `context` fields. Add a branching rule: if `question` is present, treat the call as a followup — use the prior text as context and explore the question directly. If `question` is absent, run the standard four-section brainstorm pass.

### Verify

- `ls plugin/skills/` shows expand, compress, clarify, simplify, tldr, bullets alongside brainstorm and rewrite.
- Each new SKILL.md has an Input Format section and returns `{"text": "..."}`.
- `grep "question" plugin/skills/brainstorm/SKILL.md` returns a result.

---

## Task 2: OpenAPI Contract  [Effort: 0.5 day]

### What
Add eight flat action routes to `api/openapi.yaml` with shared `TextRequest`/`TextResponse` schema components. This file drives both the Flask test assertions and `ng-openapi-gen` client generation in Task 4.

### Files
- **Modify**: `api/openapi.yaml` — add TextRequest, TextResponse, BrainstormRequest, RewriteActionRequest schemas and eight path entries

### Steps

1. Add to `components/schemas`:
   - `TextResponse`: required `text` (string) and `latencyMs` (integer).
   - `TextRequest`: required `text` (string).
   - `BrainstormRequest`: required `text`, optional `question` and `context` (all strings).
   - `RewriteActionRequest`: required `text` (string) and `style` (string enum: Concise, Technical, Executive, Narrative, Punchy).

2. Add path entries for the six uniform actions — `/api/expand`, `/api/compress`, `/api/clarify`, `/api/simplify`, `/api/tldr`, `/api/bullets`. Each: POST, operationId `<action>Text`, requestBody `TextRequest`, 200 response `TextResponse`, 400 for missing text.

3. Add `/api/brainstorm` — POST, operationId `brainstormText`, requestBody `BrainstormRequest`, 200 response `TextResponse`.

4. Add `/api/rewrite` — POST, operationId `rewriteText`, requestBody `RewriteActionRequest`, 200 response `TextResponse`, 400 for invalid style.

### Verify

- `grep -c "operationId" api/openapi.yaml` increases by exactly 8 from the baseline.
- The style enum under `RewriteActionRequest` lists exactly: Concise, Technical, Executive, Narrative, Punchy.
- `grep "TextResponse" api/openapi.yaml` appears in components and in all eight path response entries.

---

## Task 3: Flask Actions Blueprint  [Effort: 1 day]

### What
Create `api/modules/ai/routes/actions.py` — a new Blueprint at prefix `/api` with eight thin route handlers. Register it in `create_app.py` alongside the existing `ai_bp`. The two blueprints coexist until Task 5.

### Files
- **Create**: `api/modules/ai/routes/actions.py` — new blueprint, 8 handlers
- **Modify**: `api/create_app.py` — register `actions_bp` in the blueprint list
- **Create**: `api/modules/ai/routes/tests/test_actions.py` — route tests

### Steps

1. In `actions.py`, create `actions_bp = Blueprint("actions", __name__, url_prefix="/api")`. Import `require_auth`, `check_usage_limit`, `load_skill_registry`, `run_skill`, `time`, `json`, and `jsonify` from their existing locations (match the import style in `text.py`).

2. Write one handler for each of the six uniform verbs (expand, compress, clarify, simplify, tldr, bullets). Pattern per handler — max 15 lines:
   - `@actions_bp.post("/<verb>")` with `@require_auth` and `@check_usage_limit("text")`
   - Extract `text` from `request.get_json(force=True, silent=False) or {}`
   - Return 400 if text is empty
   - `load_skill_registry("<verb>")` — return 503 on FileNotFoundError
   - `run_skill("<verb>", json.dumps({"text": text}), registry)` — return 502 on RuntimeError
   - Measure with `time.monotonic()` before and after `run_skill`
   - Return `jsonify({"text": result["text"], "latencyMs": int(latency * 1000)})`

3. Write the `brainstorm` handler: same pattern, additionally extract optional `question` and `context` from body. Pass all three to skill as `json.dumps({"text": text, "question": question or "", "context": context or ""})`.

4. Write the `rewrite` handler: extract `text` and `style`. Validate style against `["Concise", "Technical", "Executive", "Narrative", "Punchy"]` — return 400 if invalid. Pass `json.dumps({"text": text, "style": style})` to the rewrite skill.

5. In `create_app.py`, add `('modules.ai.routes.actions', 'actions_bp')` to the blueprint list (line ~20, alongside the existing `ai_bp` entry).

6. Write `test_actions.py`: one happy-path test per route. Mock `run_skill` to return `{"text": "ok"}`. Assert 200 and that the response contains `text` and `latencyMs` keys. Add one test for `rewrite` with an invalid style asserting 400.

7. Rebuild: `docker compose build api && docker compose up -d api`.

### Verify

- `pytest api/modules/ai/routes/tests/test_actions.py -v` — all pass.
- `curl -X POST http://localhost:8095/api/expand -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"text": "hello world"}'` → 200 with `text` and `latencyMs`.
- `curl -X POST http://localhost:8095/api/brainstorm -d '{"text": "hello", "question": "what next?"}'` → 200.
- `curl -X POST http://localhost:8095/api/rewrite -d '{"text": "hello", "style": "Bad"}'` → 400.
- `curl -X POST http://localhost:8095/api/ai/text/rewrite -d '{"text": "x", "instructions": "y"}'` → still 200 (old route untouched).

---

## Task 4: Angular Client + AiService Cutover  [Effort: 1 day]

### What
Install `ng-openapi-gen`, generate a typed Angular client from `api/openapi.yaml`, and rewrite `ai.service.ts` as a zero-instruction facade over the generated client. Remove all instruction strings, `generate()`, and `styleAs()`.

### Files
- **Modify**: `web-ng/package.json` — add `ng-openapi-gen` dev dependency and `generate:api` script
- **Create**: `web-ng/ng-openapi-gen.json` — generator config pointing at `../api/openapi.yaml`
- **Create**: `web-ng/src/app/api/` — generated client output directory (do not hand-edit)
- **Modify**: `web-ng/src/app/services/ai.service.ts` — replace with facade over generated client
- **Modify**: `web-ng/src/app/app.component.ts` — remove instruction string from `followupBrainstorm()`

### Steps

1. `cd web-ng && npm install ng-openapi-gen --save-dev`.

2. Create `web-ng/ng-openapi-gen.json`:
   ```json
   { "input": "../api/openapi.yaml", "output": "src/app/api", "ignoreUnusedModels": false }
   ```

3. Add to `package.json` scripts: `"generate:api": "ng-openapi-gen --config ng-openapi-gen.json"`.

4. Run `npm run generate:api`. This creates `src/app/api/services/` and `src/app/api/models/`.

5. Rewrite `ai.service.ts`. Keep the class name, `@Injectable`, and `TextOperationResponse` interface. Import the generated service (likely `ApiService` or action-specific services from `src/app/api/services/`). Each method delegates in 2–3 lines using `firstValueFrom()` and the existing `AI_TIMEOUT_MS`. Methods to keep: `brainstorm(text, question?, context?)`, `expand(text)`, `compress(text)`, `clarify(text)`, `simplify(text)`, `tldr(text)`, `bullets(text)`, `styleAs(text, style)`. Delete: `generate()`, `rewrite(text, instructions)`, all inline instruction strings.

6. In `app.component.ts`, find `followupBrainstorm()`. It currently assembles an instruction string and calls `this.aiService.rewrite(text, instructionString)`. Replace with `this.aiService.brainstorm(this.currentText, question, priorResult)`. Remove the `join('\n')` block and the instruction constant.

7. `cd web-ng && npx ng build --configuration=production` — must exit 0 with no errors.

8. Open http://localhost:8095 and test: Expand, Compress, Brainstorm, Brainstorm followup (if UI has that flow), and Style As → Concise.

### Verify

- `grep -n "join\|instructions\|You are" web-ng/src/app/services/ai.service.ts` returns nothing.
- `npx ng build` exits 0.
- Expand button returns transformed text in the UI.
- Style As → Concise returns transformed text.

---

## Task 5: Dead Code Deletion  [Effort: 0.5 day]

### What
Delete the five orphan handlers from `text.py`, delete `text_prompts.py` and its tests, and remove the unused DTOs. Run in order to avoid broken imports.

### Files
- **Modify**: `api/modules/ai/routes/text.py` — delete rewrite, generate, generate-spec, iterate, lint-braindump, review handlers and their imports (keep bootstrap-project, bootstrap-status, bootstrap-cancel, bootstrap-retry)
- **Delete**: `api/modules/ai/services/text_prompts.py`
- **Delete**: test file(s) covering only the deleted routes/prompts
- **Modify**: `api/dtos/models.py` — remove unused DTOs: RewriteRequest, RewriteResponse, IterateRequest, IterateResponse, LintBraindumpRequest, ReviewRequest, ReviewResponse, GenerateRequest, GenerateResponse, GenerateSpecRequest, GenerateSpecResponse

### Steps

1. In `text.py`, delete the handler functions: `rewrite()`, `iterate()`, `lint_braindump()`, `review()`, `generate()`, `generate_spec()`. Leave the file in place — it still owns the bootstrap routes.

2. Remove the now-dead imports from the top of `text.py`: the `RewriteRequest`, `IterateRequest`, etc. DTO imports and the `generate_prompt`, `generate_spec_prompt`, `bootstrap_analysis_prompt`, `bootstrap_epic_prompt`, `bootstrap_architecture_prompt` imports from `text_prompts`.

3. Delete `api/modules/ai/services/text_prompts.py`.

4. Find and delete test files that only test the deleted handlers or `text_prompts` — run `grep -rl "text_prompts\|generate_prompt" api/` to locate them.

5. In `api/dtos/models.py`, remove the DTO classes that are now unreferenced. Confirm with `grep -r "RewriteRequest\|IterateRequest\|LintBraindumpRequest\|ReviewRequest\|GenerateRequest\|GenerateSpecRequest" api/` — all results should be zero after deletion.

6. Rebuild: `docker compose build api && docker compose up -d api`.

7. Run the full test suite: `cd api && python -m pytest -v`.

### Verify

- `grep -r "text_prompts" api/` returns nothing.
- `grep -r "generate_prompt\|generate_spec_prompt" api/` returns nothing.
- `curl -X POST http://localhost:8095/api/ai/text/rewrite -H "Authorization: Bearer <token>" -d '{}'` → 404.
- `curl -X POST http://localhost:8095/api/ai/text/generate -d '{}'` → 404.
- `curl -X POST http://localhost:8095/api/brainstorm -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"text": "hello"}'` → 200 (new routes intact).
- `python -m pytest` passes with no import errors.
