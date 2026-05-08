# Thin API Layer — Plugin-Driven AI Services

## The problem

The specview API has Python services that do two different jobs:
file I/O (read braindump, read epic, write output) and prompt engineering
(encode the 10-section guide format, encode convention rules, encode output structure).

The prompt engineering half duplicates knowledge that already lives in the plugin:
- `plugin/references/chain-conventions.md` has the adapter rules
- Agent definitions have the domain knowledge
- Skill files describe the task procedures

Every time a convention changes, both the Python prompt and the reference file need updating.
They drift. The Python code becomes the source of truth by accident.

## What we want

Python services that do only file I/O and HTTP. The AI logic — what to generate,
how to structure it, what rules to follow — lives in plugin skills and agents,
not in Python strings.

A new AI capability should mean writing a markdown skill file, not a Python module.

## What this changes

Instead of a Python service that builds a 200-line system prompt before calling the CLI,
the service calls `claude --agent chain-agent -p "generate implementation guide for epic at /path"`.
The agent knows the 10-section format because it's in its skill reference.
The Python service doesn't need to know the format at all.

The routes stay. Auth stays. Usage limiting stays. File I/O stays.
What goes away: the embedded prompt templates in `services/` and `prompts/`.

## What stays the same

The HTTP API is unchanged from the frontend's perspective.
Streaming can stay (subprocess stdout).
Background thread pattern stays.
The user experience in the Angular app is identical.

## Why this is the right time

The plugin just shipped. The agent and skill files are fresh.
The conventions are already encoded. The CLI routing via `CHAIN_AGENT` env var is wired.
This is the moment to complete the loop — make the API actually use what the plugin encodes.

## What the plugin already gives us

The chain-agent-plugin is live in this repo. It has:
- `plugin/references/chain-conventions.md` — adapter boundary, ChainResult, provider rules
- `plugin/references/flask-conventions.md` — blueprint, service layer, auth decorators
- `plugin/agents/chain-agent.md` — primary agent, already knows the full domain
- `plugin/agents/spec-backend.md` — Flask/SQLModel specialist
- `plugin/skills/spec-pipeline/SKILL.md` — orchestrates the full braindump → spec set flow

The `CHAIN_AGENT` env var is already wired in `providers/cli.py`. Setting it to `chain-agent`
routes every AI call through the agent instead of passing a raw system prompt.
The infrastructure exists — the Python services just haven't been thinned out yet.

## Concrete services to migrate

Three Python services embed the most prompt logic today:
- `api/modules/ai/workflows/spec_gen/bootstrap.py` — runs the 4-step spec chain
- `api/modules/ai/services/epic_guide.py` — builds the 10-section whole-epic guide
- `api/modules/ai/services/task_gen.py` — per-task implementation guide

Each has a corresponding prompt file in `api/modules/ai/prompts/` that encodes
structure and rules which should instead live in plugin skill files.

## Open questions

How much context to pass via `-p` vs how much the agent reads from disk.
Whether the agent should write the output file itself or return it via stdout.
How to handle the multi-step bootstrap chain (analysis → epic → architecture → timeline)
where each step depends on the previous output.
Whether `CHAIN_AGENT` should be set in production or left off until this migration is done.
What happens to the existing `prompts/` Python files — delete or keep as fallback.
