# Analysis — Thin API Layer / Plugin-Driven AI Services

## Problem Statement

The specview Flask API conflates two responsibilities in its AI service modules:

1. **File I/O** — reading braindumps, epics, architecture docs; writing generated output to `SPEC_DOC_DIR`.
2. **Prompt engineering** — encoding output structure, section formats, convention rules, and domain knowledge as Python strings.

The second responsibility duplicates knowledge that already lives in the Claude Code plugin:
- `plugin/references/chain-conventions.md` encodes adapter rules and provider constraints.
- `plugin/agents/chain-agent.md` encodes full domain knowledge and working style.
- `plugin/skills/spec-pipeline/SKILL.md` describes the pipeline procedure.

This creates two sources of truth. When a convention changes, both the Python prompt and the plugin reference file need updating. In practice, the Python code drifts — it becomes the de-facto source of truth because it runs in production while the plugin references are advisory.

## Affected Files

| File | Prompt logic embedded |
|------|-----------------------|
| `api/modules/ai/workflows/spec_gen/bootstrap.py` | 4-step chain: analysis → epic → architecture → timeline. Each step constructs a system prompt with format rules inline. |
| `api/modules/ai/services/epic_guide.py` | 10-section implementation guide. Section headers and output structure encoded in Python strings. |
| `api/modules/ai/services/task_gen.py` | Per-task implementation guide. Task context injection and output format encoded in Python. |
| `api/modules/ai/prompts/` | Python modules containing raw system prompt strings, some >200 lines. |

## Root Cause

The `CHAIN_AGENT` env var already exists in `providers/cli.py`. When set, every `claude -p` call routes through `claude --agent chain-agent`. The infrastructure for plugin-driven generation is wired — the Python services simply haven't been updated to use it.

## Goals

1. Python services own file I/O and HTTP concerns only.
2. All AI generation logic (output structure, section formats, convention rules) lives in plugin skills and agents — not in Python strings.
3. Adding a new generation capability means writing a markdown skill file, not a Python module.
4. The HTTP API surface is unchanged from the Angular frontend's perspective.
5. Streaming, background threads, and auth/usage-limiting remain in place.

## Non-Goals

- Changing the Angular frontend.
- Changing the route handlers beyond removing prompt-construction calls.
- Changing the auth or usage-limiting decorators.
- Changing the `CHAIN_PROVIDER` selection logic.
- Removing the `mock` provider (tests still need it).

## Constraints

- `CHAIN_PROVIDER=cli` in Docker — always. No SDK provider in production.
- `CHAIN_AGENT=chain-agent` must be set in the container for routed generation.
- Streaming via subprocess stdout must be preserved (`stream_generate()` path).
- Background thread state pattern (`module-level dict + snapshot()`) stays.
- No regression in response format — frontend expects the same JSON shape.

## Open Questions

| Question | Options | Decision needed by |
|----------|---------|-------------------|
| How much context to pass via `-p` vs how much the agent reads from disk? | (a) Pass full braindump in `-p`; (b) Pass only file path, agent reads disk; (c) Hybrid | Architecture |
| Should the agent write output files itself, or return via stdout? | (a) Agent writes; Python confirms; (b) Agent returns stdout; Python writes | Architecture |
| How to handle the multi-step bootstrap chain (analysis → epic → architecture → timeline) where each step depends on the previous output? | (a) One `claude` call per step, chained in Python; (b) Single call with agent orchestrating all steps | Architecture |
| What happens to `prompts/` Python files after migration? | (a) Delete; (b) Keep as fallback behind `CHAIN_AGENT` flag | Architecture |
| Should `CHAIN_AGENT` be set in production now, or only after migration is complete? | (a) Feature-flag per endpoint; (b) All-or-nothing env var | Epic |

## Success Criteria

- `api/modules/ai/prompts/` is empty or deleted.
- `api/modules/ai/services/epic_guide.py` and `task_gen.py` contain no string literals longer than one line.
- `bootstrap.py` contains no inline system prompts — only file reads and `chain.stream_generate()` calls.
- All existing pytest tests pass.
- `test_structural.py` still enforces the adapter boundary.
- A new generation type can be added by writing a skill markdown file only.
