# Claude Code Provider Plugin — Implementation Guide

This guide covers all five tasks required to ship the chain-agent-plugin.
Each task is executor-ready: concrete file paths, exact implementation steps,
tests, commit plan, and rollback.

---

## Task 1: Author Reference Files

### 1. Context

The plugin encodes conventions once so Claude never re-establishes context.
Three reference files cover the three knowledge domains: the chain adapter layer,
the Flask backend, and the Angular frontend. These are the single source of truth —
agents and skills never duplicate rules inline.

### 2. Pre-flight

- Confirm `plugin/references/` directory exists.
- Confirm no existing `chain-conventions.md`, `flask-conventions.md`, or
  `angular-conventions.md` in the plugin.

### 3. Files

**To Create:**

- `plugin/references/chain-conventions.md` — ~100 lines — adapter boundary,
  providers, ChainResult, SQLModel conventions, Alembic rules, error handling.
- `plugin/references/flask-conventions.md` — ~100 lines — blueprint structure,
  route decorators, service-layer pattern, auth, background jobs.
- `plugin/references/angular-conventions.md` — ~100 lines — signals, service
  pattern, HTTP client, polling, template control flow, markdown rendering.

**To Modify:** None.

### 4. Implementation Steps

1. Write `chain-conventions.md`: open with the adapter boundary rule (never import
   from `providers.*`). Cover providers, ChainResult, context injection,
   SQLModel patterns, Alembic rules, workflow steps, ProviderError, and quality rules.
2. Write `flask-conventions.md`: cover module structure, blueprint registration,
   `@require_auth` / `@check_usage_limit`, error handling with `APIError`,
   SQLModel patterns (service layer owns session), background job pattern, auth,
   CORS, and quality rules.
3. Write `angular-conventions.md`: cover signals vs Observable, service pattern
   (`firstValueFrom`), async component methods, polling with `clearInterval`,
   template control flow (`@if` / `@for`), markdown rendering with DOMPurify,
   styles, and quality rules.
4. Keep each file to declarative prose — no code samples larger than 5 lines.

### 5. Tests

Manual verification: open each reference file, confirm it contains all major
sections. No automated test for prose files.

### 6. Commit Plan

```
feat(plugin): add chain, flask, and angular reference files
```

### 7. Verification

Run `wc -l plugin/references/*.md` — all three files should be 80–120 lines.
Open each file and confirm the quality rules section exists.

### 8. Rollback

Delete `plugin/references/` directory. No other state changes.

### 9. Deviations Allowed

- Merge flask-conventions and chain-conventions into one file if they overlap
  excessively. Keep them separate if each is over 60 lines.

### 10. Out of Scope

- Code samples in reference files (keep prose-only).
- Linting or schema validation of reference files.

---

## Task 2: Define Agents

### 1. Context

Four agents cover the spec-doc domain. `chain-agent` is the primary backend
agent invoked by `cli.py` when `CHAIN_AGENT` is set. The three specialist agents
(`spec-backend`, `spec-frontend`, `chain-developer`) are used in interactive
sessions and by `dev-review`.

### 2. Pre-flight

- Confirm `plugin/agents/` directory exists.
- Confirm `plugin/references/` is populated (Task 1 done).

### 3. Files

**To Create:**

- `plugin/agents/chain-agent.md` — primary backend agent; loads chain and flask
  references; handles both CLI-routed calls and interactive dev.
- `plugin/agents/spec-backend.md` — Flask/SQLModel specialist; loads flask and
  chain references.
- `plugin/agents/spec-frontend.md` — Angular specialist; loads angular reference.
- `plugin/agents/chain-developer.md` — full-stack coordinator; loads all three
  references.

**To Modify:** None.

### 4. Implementation Steps

1. Write `chain-agent.md`: frontmatter with `name`, `description`, `model: claude-sonnet-4-6`.
   Body: loaded references, two responsibility categories (CLI-routed vs interactive),
   working style (5 steps), domain refusals.
2. Write `spec-backend.md`: same frontmatter shape. Body: references, responsibilities
   (blueprints, models, migrations, services), working style, quality gates as a
   "refuse if violated" list, domain refusals.
3. Write `spec-frontend.md`: same shape. Body: angular reference only, responsibilities
   (signals, service methods, templates, polling, dark mode), quality gates, refusals.
4. Write `chain-developer.md`: loads all three references. Body: "when to use this agent"
   section, working style (bottom-up: chain → service → route → Angular), refusals.
5. Agent bodies are 30–60 lines. No code blocks longer than 5 lines.

### 5. Tests

Manual: open `chain-agent.md` in Claude Code and confirm it loads without parse error.
Check frontmatter fields are valid YAML.

### 6. Commit Plan

```
feat(plugin): add chain-agent, spec-backend, spec-frontend, chain-developer agents
```

### 7. Verification

Run `wc -l plugin/agents/*.md` — all files 30–80 lines.
Confirm frontmatter has `name`, `description`, `model` fields in each file.

### 8. Rollback

Delete `plugin/agents/` directory.

### 9. Deviations Allowed

- Combine `spec-backend` and `chain-developer` if they overlap too much (unlikely).

### 10. Out of Scope

- Agent-to-agent communication protocols.
- Agent versioning.

---

## Task 3: Implement Dev Skills

### 1. Context

Five skills cover the development lifecycle: build check, test run, Alembic migration,
code review (fan-out), and spec-pipeline (braindump → spec set). SKILL_MAP.md is the
master index.

### 2. Pre-flight

- Confirm `plugin/skills/` directory exists with subdirectories for each skill.
- Confirm agents are in place (Task 2 done).

### 3. Files

**To Create:**

- `plugin/skills/dev-build/SKILL.md` — stack detection + pytest collect / ng build.
- `plugin/skills/dev-test/SKILL.md` — pytest or ng test, module-scoped.
- `plugin/skills/dev-migrate/SKILL.md` — Alembic scaffold + review gate + apply + verify.
- `plugin/skills/dev-review/SKILL.md` — 3-agent fan-out, synthesized report.
- `plugin/skills/spec-pipeline/SKILL.md` — bootstrap-project API orchestration.
- `plugin/skills/SKILL_MAP.md` — master index with workflow diagram.

**To Modify:** None.

### 4. Implementation Steps

1. Write each `SKILL.md` using the financing-plugin shape: frontmatter (`name`,
   `description`), then sections: STOP rule, Parameters, Procedure (numbered steps),
   Output Format, Abort Conditions, Allowed Tools.
2. `dev-build`: detect stack from cwd markers; backend runs `pytest --collect-only`;
   frontend runs `ng build --configuration production`.
3. `dev-test`: detect stack; backend runs `pytest modules/{name}/` if inside a module;
   frontend runs `ng test --watch=false`.
4. `dev-migrate`: auto-generate → review gate (check downgrade) → apply → verify current.
5. `dev-review`: gather `git diff --name-only`, classify by layer, fan out to three
   agents, synthesize with Critical/Warnings/OK groups.
6. `spec-pipeline`: health check → `POST /api/ai/text/bootstrap-project` → poll
   every 5s → confirm on `GET /api/projects/{id}`.
7. Write `SKILL_MAP.md`: two workflow diagrams, two tables (dev-tools + spec-pipeline),
   agents table, quick reference block.

### 5. Tests

Manual: invoke `/dev-build` in Claude Code against the specview repo. Confirm it
runs `pytest --collect-only` for the backend. Check output format matches the spec.

### 6. Commit Plan

```
feat(plugin): add dev-build, dev-test, dev-migrate, dev-review, spec-pipeline skills
```

### 7. Verification

- `wc -l plugin/skills/**/*.md` — each SKILL.md 30–80 lines.
- SKILL_MAP.md references all 5 skills.
- `/dev-review` smoke: run in specview root, confirm 3 agents are spawned.

### 8. Rollback

Delete `plugin/skills/` directory.

### 9. Deviations Allowed

- `dev-migrate` may skip the H2 boot-validation gate (financing-plugin specific);
  substitute with `alembic current` as the verification step.

### 10. Out of Scope

- ADO / GitHub issue creation (not in specview workflow).
- Feature-lifecycle skills (PRD, requirement, review) — spec-doc uses its own pipeline.

---

## Task 4: Wire Session-Start Hook

### 1. Context

The SessionStart hook runs when Claude Code opens a session. It detects which stack
is active (backend / frontend / root) and emits a JSON context block. Claude uses
this to know which reference files to load without being told every session.

### 2. Pre-flight

- Confirm Node.js is available: `node --version`.
- Confirm `plugin/hooks/` directory exists.

### 3. Files

**To Create:**

- `plugin/hooks/session-start.mjs` — ESM script; detects git root and cwd stack;
  emits JSON; silent on error.
- `plugin/hooks/hooks.json` — registers the hook under `SessionStart`.
- `plugin/.claude-plugin/plugin.json` — plugin metadata.

**To Modify:** None.

### 4. Implementation Steps

1. Write `hooks.json`:
   ```json
   {
     "hooks": {
       "SessionStart": [{
         "hooks": [{"type": "command", "command": "node ${CLAUDE_PLUGIN_ROOT}/hooks/session-start.mjs"}]
       }]
     }
   }
   ```
2. Write `session-start.mjs` (~60 lines):
   - `findGitRoot(cwd)`: walk up until `.git` found.
   - `classifyStack(gitRoot)`: check for `api/conftest.py` (backend) or
     `web-ng/angular.json` (frontend).
   - `detectCwd(cwd)`: check if path contains `/api/` or `/web-ng/`.
   - `buildContext(gitRoot, stack, cwdStack)`: choose reference files.
   - Wrap main block in `try { ... } catch { /* silent fail */ }`.
   - Emit `JSON.stringify(ctx) + '\n'` to stdout.
3. Write `plugin.json` with name, description, version, author.

### 5. Tests

```bash
node plugin/hooks/session-start.mjs
```

From specview root: emits JSON with all three references.
From `api/modules/ai/`: emits JSON with chain + flask references only.
From `web-ng/src/`: emits JSON with angular reference only.

### 6. Commit Plan

```
feat(plugin): wire SessionStart hook and plugin.json
```

### 7. Verification

Run the hook from each of the three cwd positions. Confirm correct `stack` and
`references` fields. Confirm no output when hook encounters an error (rename `.git`
temporarily to test).

### 8. Rollback

Delete `plugin/hooks/` and `plugin/.claude-plugin/`.

### 9. Deviations Allowed

- Output a markdown block instead of JSON if Claude Code's hook protocol changes.
- Omit the gitRoot detection if the repo structure is always flat.

### 10. Out of Scope

- Gradle module detection (financing-plugin specific).
- Frontend module detection below the `src/app/` level.

---

## Task 5: Enhance cli.py

### 1. Context

`api/modules/runtime/chain/providers/cli.py` currently calls the `claude` CLI with
a raw `--system-prompt` string containing the full chain conventions on every call.
Adding `CHAIN_AGENT` env var routes the call through `claude --agent <name>` instead,
offloading convention knowledge to the agent definition. The system prompt is no
longer sent — the agent file is the system prompt.

### 2. Pre-flight

- Confirm `api/modules/runtime/chain/providers/cli.py` exists.
- Confirm `plugin/agents/chain-agent.md` is in place (Task 2 done).
- Confirm tests pass before touching cli.py: `pytest api/modules/runtime/chain/ -v`.

### 3. Files

**To Modify:**

- `api/modules/runtime/chain/providers/cli.py` — add `_CHAIN_AGENT` constant and
  branch in `_build_cmd`.

### 4. Implementation Steps

1. Add constant after `_CLI_KEY`:
   ```python
   _CHAIN_AGENT = os.environ.get("CHAIN_AGENT", "")  # e.g. "chain-agent"
   ```
2. Modify `_build_cmd(system)`:
   ```python
   def _build_cmd(system: str) -> list[str]:
       if _CHAIN_AGENT:
           cmd = ["claude", "--agent", _CHAIN_AGENT, "-p", "--output-format", "text"]
       else:
           cmd = ["claude", "-p", "--output-format", "text"]
           if _CLI_KEY:
               cmd.append("--bare")
           if system:
               cmd.extend(["--system-prompt", system])
       return cmd
   ```
3. No other changes. `create_message` and `stream_message` are unchanged.

### 5. Tests

The existing `test_structural.py` and provider tests cover the unchanged path.
Add one test for the agent path:

```python
# api/modules/runtime/chain/providers/tests/test_cli.py
import os
from unittest.mock import patch

def test_build_cmd_with_chain_agent(monkeypatch):
    monkeypatch.setenv("CHAIN_AGENT", "chain-agent")
    import importlib
    import api.modules.runtime.chain.providers.cli as cli_mod
    importlib.reload(cli_mod)
    cmd = cli_mod._build_cmd("any system prompt")
    assert "--agent" in cmd
    assert "chain-agent" in cmd
    assert "--system-prompt" not in cmd
```

### 6. Commit Plan

```
feat(plugin/cli): route cli.py through --agent when CHAIN_AGENT is set
```

### 7. Verification

Set `CHAIN_AGENT=chain-agent` in `docker-compose.override.yml` (api environment).
Restart the API container. Trigger a spec generation. Confirm in container logs
that the `claude` call includes `--agent chain-agent`.

### 8. Rollback

Remove the `_CHAIN_AGENT` constant and the `if _CHAIN_AGENT:` branch from `_build_cmd`.
Or: unset `CHAIN_AGENT` from the environment (the fallback path is identical to
the original code).

### 9. Deviations Allowed

- Use a different env var name if `CHAIN_AGENT` conflicts with another system variable.
- Pass `--model` to the agent call if the backend needs to override the agent's default.

### 10. Out of Scope

- Modifying `adapter.py` — the adapter boundary is unchanged.
- Streaming support for the agent path — `--agent` CLI routing does not support
  streaming in v1; the CLI provider never streamed anyway.
- Removing the system-prompt path — it remains as the fallback for non-agent sessions.
