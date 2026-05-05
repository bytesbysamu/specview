I now have complete context. The existing v2 spec is well-written, and I've verified all the source material. Let me produce the final implementation guide, incorporating the actual port-source code from `server.js` and the real file contents from `builder.md`/`principles.md`.

# Task 4: Braindump → Docs Chain

**Purpose**: Port spec-doc's multi-file generation pipeline (braindump → 5 linked markdown files) into a chain definition with three steps (lint, generate, review), implement the `===FILE:===` marker parser as an anti-corruption layer, and create all supporting context files.

**Effort**: 1 day

**Dependencies**: Task 1 (Context Block Loader) and Task 2 (Chain Definition Schema + Runner) — both must be merged. Task 1 provides `load_block(name)` / `load_blocks(names)`. Task 2 provides `STEP_HANDLERS` dispatch with `rewrite`, `generate`, and `review` handlers, `load_definition(chainId)`, `run_definition(chainId, input, user=)`, and the `POST /api/text/chain` endpoint.

**Parallel With**: Task 3 (Deep Humanize), Task 5 (Rewrite + Review) — all three are independent once Tasks 1+2 land.

**Blocks**: Task 6 (Chain Mode UI) — specifically the tabbed multi-file output area, which needs a chain that returns `files` to render.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task ports spec-doc's `generate-spec` endpoint — the feature that takes a brain dump and produces 5 linked spec files (spec-index, analysis, epic, architecture, timeline) in a single LLM call — into the Bubls chain runner. The pipeline becomes a 3-step chain: (1) lint the braindump for structural gaps, (2) generate multi-file output with builder context and principles injected, (3) self-review against a quality rubric. The LLM returns marker-delimited text (`===FILE: {name}===`), which a server-side parser converts to structured `[{name, content}]` before it reaches the frontend. This is the anti-corruption layer the architecture doc prescribes. The task has one code addition (file-marker parser + runner wiring) and six data files (4 context prompts, 1 rubric, 1 chain definition). All three prompts are ported from working spec-doc code: the generation template from `server.js:718-998`, the lint prompt from `server.js:1142-1189`, and the review rubric from `server.js:1023-1084`.

**Trade-offs considered**:
- **Multiple LLM calls per file** (one call per doc type) — rejected: spec-doc's single-call approach is proven, cheaper (1 call vs 5), and produces internally consistent cross-references between docs. The architecture doc confirms this choice.
- **Structured JSON output from the LLM** for multi-file content — rejected: Claude is less reliable at producing valid JSON for long-form content (4000+ tokens). Marker-delimited plain text with server-side parsing is the proven pattern from spec-doc.
- **File-marker parsing in the route layer vs the runner** — runner chosen: `outputMode` is a chain-definition concern, not a route concern. The route returns the runner's structured output directly. This keeps the anti-corruption layer at the right boundary.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/bubls
git status                                          # flag unrelated M/?? entries
git log -1 --format='%H' > /tmp/bubls-task4-sha     # rollback anchor
cd server && python -m pytest -q 2>&1 | tail -5     # baseline pass count
```

Confirm Task 1 and Task 2 are merged:

```bash
# Context loader
python -c "from modules.context.loader import load_block, load_blocks; print('loader ok')"

# Chain runner with STEP_HANDLERS + definition loading
python -c "from modules.chain.definition_runner import load_definition, run_definition, STEP_HANDLERS; print('runner ok')"

# All three handlers exist
python -c "from modules.chain.definition_runner import STEP_HANDLERS; assert 'review' in STEP_HANDLERS; assert 'generate' in STEP_HANDLERS; assert 'rewrite' in STEP_HANDLERS; print('handlers ok')"
```

Confirm directory structure exists:

```bash
ls server/context/manifest.json
ls server/context/prompts/
ls server/context/rubrics/          # may not exist yet — Step 3 will create it
ls server/modules/chain/definitions/
```

**If any import fails**: Task 1 or Task 2 is not merged. STOP.

**Note**: If `definition_runner` is named `runner` instead, adapt all imports throughout this guide. The key symbols are `load_definition`, `run_definition`, `STEP_HANDLERS`, and `ChainRunResult`.

**Baseline recorded**: write the pytest pass count into the first commit body.

---

## 3. Files

### To Create (new)

- `server/context/prompts/braindump-lint.md` — structural pre-flight lint prompt; ported from `spec-doc/server.js:1142-1189`
- `server/context/prompts/braindump-to-docs.md` — multi-file generation prompt with `===FILE: {name}===` markers; ported from `spec-doc/server.js:718-998`
- `server/context/prompts/builder.md` — builder profile context block; content from `spec-doc/builder.md`
- `server/context/prompts/principles.md` — architecture principles context block; content from `spec-doc/principles.md` (trimmed to patterns-to-apply)
- `server/context/prompts/references.md` — cross-project reference pointers; minimal for v1
- `server/context/rubrics/quality.md` — 6-dimension quality rubric for review step; ported from `spec-doc/server.js:1023-1084`
- `server/modules/chain/file_parser.py` — `parse_file_markers(text) -> list[dict[str, str]]` anti-corruption layer
- `server/modules/chain/definitions/braindump-to-docs.json` — 3-step chain definition (lint → generate → review), `outputMode: "multi-file"`
- `server/modules/chain/tests/test_file_parser.py` — 11 unit tests for the marker parser
- `server/modules/chain/tests/test_braindump_to_docs.py` — 14 chain-level tests covering definition shape, context resolution, structural invariants

### To Modify

- `server/context/manifest.json` — add 6 entries: `braindump-lint`, `braindump-to-docs`, `builder`, `principles`, `references`, `quality-rubric`
- `server/modules/chain/definition_runner.py` — import `parse_file_markers` from `.file_parser`; call it when `definition.output_mode == "multi-file"` to convert raw LLM text to structured `files` list on `ChainRunResult`

### To Leave Alone

- `server/modules/chain/adapter.py` — adapter boundary intact; chain steps call `adapter.generate()` through `STEP_HANDLERS`, no changes needed
- `server/modules/chain/providers/` — adapter boundary; runner never imports providers directly
- `server/modules/chain/signals.py` — `chainCompleted` observer unchanged; emitted by runner after each run
- `server/modules/chain/types.py` — `ChainResult` ACL unchanged
- `server/modules/chain/__init__.py` — only update if re-exporting `parse_file_markers` is needed by another module (unlikely for Task 4)
- `server/modules/context/loader.py` — no changes; this task only adds files the loader reads
- `server/modules/text/chain_routes.py` — endpoint already registered by Task 2; no route changes
- `server/modules/text/chain_service.py` — orchestration layer reads `ChainRunResult` which now may have `files`; it passes the result through
- `server/app.py` — no new blueprints; chain endpoint already registered
- `src/app/` — zero frontend work in Task 4; tabbed output is Task 6

---

## 4. Implementation Steps

### Step 1: Create the braindump-lint context file

**Action**: Port the braindump lint prompt from `spec-doc/server.js:1142-1189` (function `buildBraindumpLintPrompt`) into a standalone markdown file. Adapt: remove `${principles}` and `${references}` template interpolation (the chain runner injects those as separate context blocks). Keep the JSON output schema, 5 dimensions, and readiness thresholds verbatim.

**File**: `server/context/prompts/braindump-lint.md` (new)

**Pattern** (port from `spec-doc/server.js:1142-1189`):
```markdown
You are a structural reviewer for braindumps that will feed a spec-generation pipeline.
Your job: flag gaps that will produce a bad epic + bad tasks. Do NOT rewrite the braindump. Do NOT judge ideas on merit — only on shape and structural completeness.

## YOUR TASK

Return ONLY valid JSON with this exact shape:

{
  "readiness": "ready" | "needs_rewrite" | "ready_with_caveats",
  "length": { "lines": <number>, "verdict": "ok" | "too_long" | "too_short" },
  "flags": [
    { "dim": "port_sources", "pass": <bool>, "note": "<max 100 chars>" },
    { "dim": "out_of_scope_explicit", "pass": <bool>, "note": "..." },
    { "dim": "invents_vs_cites", "pass": <bool>, "note": "..." },
    { "dim": "consumers_named", "pass": <bool>, "note": "..." },
    { "dim": "principles_contradicted", "pass": <bool>, "note": "..." }
  ],
  "top_3_fixes": ["...", "...", "..."]
}

## Dimensions explained

- **port_sources**: If the braindump uses words like "port", "copy", "mirror", "adapt from", does it cite specific files with line-range references? If no port language, pass=true (N/A).
- **out_of_scope_explicit**: Does the braindump name what it DOES NOT cover and why? A section titled "Out of scope" / "Explicitly out of scope" / "Not in this epic" counts.
- **invents_vs_cites**: Does the braindump propose new abstractions (declarative types, DB tables, framework-like infra) without naming a current consumer for each? Pass=true if every proposed abstraction has a named consumer.
- **consumers_named**: Does every proposed feature or component have a named user or caller? Features with "someone might want..." fail. Features with "task N uses this" pass.
- **principles_contradicted**: Does the braindump propose things the injected PRINCIPLES block explicitly forbids (e.g., "use Supabase" when principles say Never Supabase)? Pass=true if no contradictions.

## Readiness thresholds

- **"ready"**: all 5 flags pass
- **"ready_with_caveats"**: 3-4 flags pass, notes are actionable
- **"needs_rewrite"**: 2+ flags fail, especially invents_vs_cites or principles_contradicted

top_3_fixes must be concrete — "add file refs to the 'port from humanize-me' mention" beats "improve port language".

Return ONLY the JSON object. No preamble, no prose.
```

**Verify**:
```bash
wc -l server/context/prompts/braindump-lint.md    # expect 30-40 lines
head -2 server/context/prompts/braindump-lint.md   # "You are a structural reviewer"
```

---

### Step 2: Create the braindump-to-docs generation context file

**Action**: Port the multi-file generation prompt from `spec-doc/server.js:718-998`. This is the core prompt that takes a braindump and produces 5 linked spec files using `===FILE: {name}===` markers. Adapt: remove `${builderProfile}` and `${principles}` template interpolation (the runner injects those as separate context blocks via the chain definition's `context` array). Preserve the `===FILE:===` / `===END===` marker format exactly.

**File**: `server/context/prompts/braindump-to-docs.md` (new)

**Pattern** (port from `spec-doc/server.js:718-998`, removing template variables):
```markdown
You are a specification document generator following structured documentation guidelines.

## YOUR TASK

Generate a COMPLETE capability folder with these files. Use EXACT format with file markers.

===FILE: spec-index.md===
---
sidebar_position: 0
---

# [Capability Name]

> One-line description

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design |
| [Timeline](./timeline.md) | Status tracking |

## Overview

2-3 paragraphs: what this capability does, why it matters, who benefits.

## Related Documents

- [Analysis](./analysis.md)

===FILE: analysis.md===
---
sidebar_position: 1
---

# [Capability Name] — Analysis

**Purpose**: Identify problems driving this capability.

**Date**: [Current date]

---

## Summary

2-3 sentences. Total issues, severity breakdown.

---

## Issue Breakdown

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| [Problem] | HIGH/MEDIUM | Task N |

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

===FILE: epic.md===
---
sidebar_position: 2
---

# [Capability Name] — Epic

**Purpose**: Define scope and tasks for [capability].

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

2-3 paragraphs on why this matters. End with value proposition.

---

## Scope

### What This Epic Covers
- Item 1
- Item 2
- Item 3

### What This Epic Does NOT Cover
- Exclusion 1
- Exclusion 2

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **[Task Name]** | None | — | 1 day | High |
| 2 | **[Task Name]** | 1 | 3 | 2 days | High |
| 3 | **[Task Name]** | 1 | 2 | 1 day | Medium |

### Task Details

#### Task 1: [Task Name]
Brief description of what this task accomplishes.

#### Task 2: [Task Name]
Brief description of what this task accomplishes.

#### Task 3: [Task Name]
Brief description of what this task accomplishes.

---

## Success Criteria

- Criterion 1
- Criterion 2
- Criterion 3

---

## Non-Goals

- Non-goal 1
- Non-goal 2

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===FILE: architecture.md===
---
sidebar_position: 3
---

# [Capability Name] — Solution Architecture

**Purpose**: Technical design for [capability].

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

High-level description of the system design and how components fit together.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| [Principle 1] | How it applies |
| [Principle 2] | How it applies |

---

## Component Design

### [Component Name]

**Purpose**: What this accomplishes

**Components**:
- `FileName.ts` — Description
- `ConfigFile.yml` — Description

**Patterns**: Patterns used

---

## Execution Flow

```
[Phase 1]
   Task 1 → Task 2
             Task 3
                │
[Phase 2]       ▼
   Task 4 ──→ Task 5
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Decision 1] | [Choice] | [Why] |
| [Decision 2] | [Choice] | [Why] |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

===FILE: timeline.md===
---
sidebar_position: 4
---

# [Capability Name] — Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | [Task Name] | backlog | |
| 2 | [Task Name] | backlog | |
| 3 | [Task Name] | backlog | |

---

## Status Legend

- `backlog` — Not started
- `in_progress` — Currently working
- `done` — Completed
- `blocked` — Waiting on dependency

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| | | | |

===END===

Generate ALL 5 files with COMPLETE, detailed content based on the user's input.
- Each file should be substantial (300+ words)
- Tasks should be specific and actionable
- Architecture should include real technical details
- Be specific to the user's input, not generic
```

**Verify**:
```bash
grep -c "===FILE:" server/context/prompts/braindump-to-docs.md   # expect 5
grep -c "===END===" server/context/prompts/braindump-to-docs.md  # expect 1
```

---

### Step 3: Create supporting context files (builder, principles, references, quality rubric)

**Action**: Create four supporting context files. The builder and principles files are trimmed versions of `spec-doc/builder.md` and `spec-doc/principles.md` respectively — only the sections relevant for AI generation (exclude the full code examples and engineering-discipline sections that are for human developers). The references file is a minimal pointer for v1. The quality rubric is ported from `spec-doc/server.js:1023-1084`.

**Files**: `server/context/prompts/builder.md` (new), `server/context/prompts/principles.md` (new), `server/context/prompts/references.md` (new), `server/context/rubrics/quality.md` (new)

Create `server/context/rubrics/` directory if it doesn't exist:
```bash
mkdir -p server/context/rubrics
```

**Pattern** for `server/context/prompts/builder.md` (trimmed from `spec-doc/builder.md`):
```markdown
# Builder Profile

## Who I Am
- Role: Full-stack developer, solo founder building SaaS products
- Style: Minimal, ship fast, validate before expanding
- Pattern: Ship in < 1 week, validate with 200 users, iterate from signal

## Primary Stack
- Frontend: Angular 19 + Ionic 8 + Capacitor 7 (web + native iOS from same codebase)
- Database: Neon Postgres with pgvector (shared instance, EU Central 1)
- Backend: Python (Flask) for product APIs, Express for tooling
- AI: Claude API (Anthropic) for generation/curation, OpenAI for embeddings

## Infrastructure
- CI/CD: GitHub Actions with path-change detection (dorny/paths-filter)
- Deployment: Coolify webhooks for web, Fastlane for iOS TestFlight
- Docker Compose for local dev environments

## Solution Architecture Preferences
- Claude IS the algorithm (no ML pipelines, no embeddings-only search for v1)
- APIs over scraping (reliable, structured data first)
- Auth: Neon Postgres only. Magic link tokens (email + UUID). Never Supabase, never Firebase
- Batch over real-time (where weekly/daily cadence fits the use case)
- pgvector from day one (accumulate embeddings even if not using them yet)
- Ship the car, not the engine — no infrastructure before first user

Use this context to inform technology choices and architecture decisions.
```

**Pattern** for `server/context/prompts/principles.md` (trimmed from `spec-doc/principles.md`):
```markdown
# Architecture Principles (non-negotiable)

## Structure
- **Monorepo Always**: one repo per product, one PR = one feature
- **Feature = Bounded Context**: each feature is a lazy-loaded route with own models, service, mock, tests. No cross-feature imports. Shared code lives in `shared/`
- **Module Registry via Routes**: adding feature = new folder + one line in app.routes.ts
- **Feature Guard with Null Object**: disabled feature → paywall/upgrade page, never 404

## Patterns to Apply
- **Adapter**: every service adapts between UI and backend. Mock mode via env flag
- **Strategy**: each feature declares which AI backend it needs; swap without touching UI
- **Registry**: user.enabled_features array for per-user gating
- **Observer**: features publish signals/events; never import each other
- **Anti-Corruption Layer**: mapper isolates domain from external API response formats

## Frontend Rules
- Standalone Components, OnPush, Signals — no NgModules
- Constructor injection via inject() — no mutable service refs
- data-test selectors only in tests — never query by class, id, or tag

## Backend Rules
- Flask, Minimal: ~30 lines per feature endpoint. Factory pattern
- Neon Postgres for Everything — no Supabase, no Firebase
- OpenAPI-First with generated DTOs
- Always ORM, never raw SQL — SQLAlchemy/SQLModel
- Magic link auth: email + UUID token, no passwords, no OAuth

The architecture document MUST follow these principles. Every design decision must align with these patterns.
```

**Pattern** for `server/context/prompts/references.md`:
```markdown
# Reference Materials

Cross-project code and patterns available for porting:

## humanize-me (Python + Flask + Claude)
- `backend/services/claude.py` — unified Claude provider (create_message, stream_message)
- `backend/services/humanizer.py` — three-pass sequential chain
- `backend/app.py` — Flask streaming routes

## spec-doc (Node.js + Angular)
- `server.js` — AI adapter pattern (mock/CLI/remote providers), builder context injection
- Multi-file generation with `===FILE: {name}===` markers
- Quality review against 6-dimension rubric

## Patterns to reuse
- Adapter boundary for AI providers (one entry point, env-flag gated)
- Anti-Corruption Layer for LLM output (parse before returning to caller)
- Sequential chain (output of step N feeds step N+1)
```

**Pattern** for `server/context/rubrics/quality.md` (ported from `spec-doc/server.js:1023-1084`):
```markdown
You are a quality reviewer for specification documents following structured documentation methodology.

Score each dimension 1-5 and list specific violations.

## 1. STRUCTURAL COMPLETENESS
Are all required sections present for each document type?
- Analysis: Summary, Issue Breakdown, Related Docs
- Epic: Business Value, Scope (in/out), Task Table (with Parallel column), Success Criteria, Non-Goals
- Architecture: Overview, Design Principles, System Boundaries, Component Design, Tech Stack, Design Decisions, Execution Flow

## 2. CONTENT ROUTING COMPLIANCE
Is content in the RIGHT document?
- Status words in Epic or Architecture? VIOLATION
- Code blocks in Architecture? VIOLATION
- Design decisions in Epic? VIOLATION
- Business value in Architecture? VIOLATION

## 3. CROSS-REFERENCE INTEGRITY
Do documents reference each other correctly?
- Every doc should have a Related Documents section
- Links should point to sibling files (./epic.md, ./architecture.md)
- Cross-references must be bidirectional

## 4. TASK SPECIFICITY
Are tasks actionable?
- Each task should have a clear deliverable
- Dependencies should be explicit
- Effort estimates present

## 5. SCOPE DISCIPLINE
Are boundaries clear?
- "What This Epic Does NOT Cover" section present and specific
- Non-Goals section present
- No scope creep indicators

## 6. TECHNICAL DEPTH
Does architecture contain real decisions?
- Design Decisions table with rationale
- Component descriptions reference actual files/patterns
- Tech stack specified

## OUTPUT FORMAT (valid JSON)

Return ONLY valid JSON, nothing else:
{
  "dimensions": {
    "structural_completeness": { "score": 1-5, "violations": ["..."] },
    "content_routing": { "score": 1-5, "violations": ["..."] },
    "cross_references": { "score": 1-5, "violations": ["..."] },
    "task_specificity": { "score": 1-5, "violations": ["..."] },
    "scope_discipline": { "score": 1-5, "violations": ["..."] },
    "technical_depth": { "score": 1-5, "violations": ["..."] }
  },
  "overall_score": 1-5,
  "level": "gold|silver|bronze|needs_work",
  "top_3_fixes": ["...", "...", "..."]
}
```

**Verify**:
```bash
ls server/context/prompts/builder.md server/context/prompts/principles.md server/context/prompts/references.md server/context/rubrics/quality.md
wc -l server/context/rubrics/quality.md    # expect 45-60 lines
```

---

### Step 4: Register all new context blocks in the manifest

**Action**: Add 6 entries to `server/context/manifest.json`: `braindump-lint`, `braindump-to-docs`, `builder`, `principles`, `references`, `quality-rubric`. Merge with existing entries from Task 1 (humanize-pass-1/2/3) without overwriting them.

**File**: `server/context/manifest.json` (modify)

**Pattern** (the final manifest must contain at minimum these entries alongside any existing ones):
```json
{
  "braindump-lint": "prompts/braindump-lint.md",
  "braindump-to-docs": "prompts/braindump-to-docs.md",
  "builder": "prompts/builder.md",
  "principles": "prompts/principles.md",
  "references": "prompts/references.md",
  "quality-rubric": "rubrics/quality.md"
}
```

**Verify**:
```bash
python -c "
import json
with open('server/context/manifest.json') as f:
    m = json.load(f)
required = ['braindump-lint', 'braindump-to-docs', 'builder', 'principles', 'references', 'quality-rubric']
for name in required:
    assert name in m, f'missing: {name}'
    print(f'  {name} -> {m[name]}')
print('manifest ok')
"
```

Then verify the loader resolves all new blocks (requires `CONTEXT_PROVIDER` not set to `mock`, or mock fixtures must include the new names):
```bash
CONTEXT_PROVIDER=file python -c "
from modules.context.loader import load_blocks
blocks = load_blocks(['braindump-lint', 'braindump-to-docs', 'builder', 'principles', 'references', 'quality-rubric'])
for name, content in blocks.items():
    assert len(content) > 0, f'{name} is empty'
    print(f'{name}: {len(content)} chars')
print('all 6 blocks loaded ok')
"
```

---

### Step 5: Implement the file-marker parser

**Action**: Create the `parse_file_markers` function. This is the anti-corruption layer: it converts LLM multi-file output (marker-delimited text) into structured `[{name, content}]` objects. Ported from the same `===FILE: {name}===` convention used in `spec-doc/server.js:729-992`. The parser uses a compiled regex, strips `===END===` markers, excludes empty-content files, and raises `ValueError` if no markers are found.

**File**: `server/modules/chain/file_parser.py` (new)

**Pattern**:
```python
"""Anti-corruption layer: parse ===FILE: {name}=== markers from LLM output.

LLM multi-file output is a single string with marker-delimited sections.
This parser converts it to structured [{name, content}] before the response
reaches the frontend. The LLM output format never leaks past this boundary.

Ported from spec-doc/server.js generate-spec endpoint (lines 729-992),
which uses the same ===FILE: {name}=== / ===END=== marker convention.
"""
from __future__ import annotations

import re

_FILE_MARKER = re.compile(r"^===FILE:\s*(.+?)\s*===$", re.MULTILINE)
_END_MARKER = re.compile(r"^===END===$", re.MULTILINE)


def parse_file_markers(text: str) -> list[dict[str, str]]:
    """Split marker-delimited text into structured file objects.

    Args:
        text: LLM output containing ``===FILE: name===`` markers.

    Returns:
        List of ``{"name": str, "content": str}`` dicts. Empty-content
        files are excluded. Order matches appearance in the input.

    Raises:
        ValueError: if no ``===FILE:===`` markers found in the input.
    """
    # Strip trailing ===END=== if present
    text = _END_MARKER.sub("", text).rstrip()

    markers = list(_FILE_MARKER.finditer(text))
    if not markers:
        raise ValueError(
            "No ===FILE: {name}=== markers found in output. "
            "Expected multi-file format but got plain text."
        )

    files: list[dict[str, str]] = []
    for i, match in enumerate(markers):
        name = match.group(1).strip()
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        if content:
            files.append({"name": name, "content": content})

    return files
```

**Verify**:
```bash
python -c "
from modules.chain.file_parser import parse_file_markers

sample = '''===FILE: analysis.md===
# Analysis
Some content here.

===FILE: epic.md===
# Epic
More content.

===END==='''

files = parse_file_markers(sample)
assert len(files) == 2
assert files[0]['name'] == 'analysis.md'
assert '# Analysis' in files[0]['content']
assert files[1]['name'] == 'epic.md'
print('parser ok')
"
```

---

### Step 6: Wire file-marker parsing into the runner for multi-file output

**Action**: Modify `server/modules/chain/definition_runner.py` to import `parse_file_markers` and call it when `definition.output_mode == "multi-file"`. The runner's `ChainRunResult` already has a `files` field (from Task 2's spec); this step populates it by parsing the final step's output through the file-marker parser.

**File**: `server/modules/chain/definition_runner.py` (modify)

**Pattern** (add import at top):
```python
from .file_parser import parse_file_markers
```

Then in `run_definition`, after the step loop produces `final_output`, before building the `ChainRunResult`:
```python
# After all steps complete, final_output holds the last step's text
if definition.output_mode == "multi-file":
    files = parse_file_markers(final_output)
    return ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        files=files,
        step_count=len(definition.steps),
        input_length=len(user_input),
        output_length=len(final_output),
    )
else:
    return ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        result=final_output,
        step_count=len(definition.steps),
        input_length=len(user_input),
        output_length=len(final_output),
    )
```

The exact field names and constructor shape depend on Task 2's `ChainRunResult` implementation. The invariants to preserve: (1) multi-file definitions trigger `parse_file_markers` on the raw output, (2) the result object carries a `files` list with `name` and `content` keys, (3) single-file definitions continue to return `result` as a string.

**Verify**:
```bash
python -c "
from modules.chain.definition_runner import run_definition
from modules.chain.file_parser import parse_file_markers
print('import chain ok — parser wired into runner')
"
```

---

### Step 7: Create the braindump-to-docs chain definition

**Action**: Create the chain definition JSON. 3 steps: (1) review/lint with `braindump-lint` context, (2) generate with `builder` + `principles` + `references` + `braindump-to-docs` context, (3) review/score with `quality-rubric` context. Output mode is `multi-file`.

**File**: `server/modules/chain/definitions/braindump-to-docs.json` (new)

**Pattern**:
```json
{
  "id": "braindump-to-docs",
  "name": "Brain Dump \u2192 Docs",
  "steps": [
    { "op": "review", "context": ["braindump-lint"], "outputKey": "lint" },
    { "op": "generate", "context": ["builder", "principles", "references", "braindump-to-docs"] },
    { "op": "review", "context": ["quality-rubric"], "outputKey": "score" }
  ],
  "outputMode": "multi-file"
}
```

**Verify**:
```bash
python -c "
from modules.chain.definition_runner import load_definition
d = load_definition('braindump-to-docs')
assert len(d.steps) == 3
assert d.steps[0].op == 'review'
assert d.steps[1].op == 'generate'
assert d.steps[2].op == 'review'
assert d.output_mode == 'multi-file'
print(f'Chain: {d.name}, steps: {len(d.steps)}, output: {d.output_mode}')
"
```

Note: if `load_definition` returns a dict instead of a dataclass, adapt the attribute access (e.g., `d["steps"]` instead of `d.steps`). The verify command should confirm the definition loads with the correct shape.

---

### Step 8: Write file-parser unit tests

**Action**: Create `test_file_parser.py` with 11 tests covering: happy path (2 files, 5 files, preserve order), edge cases (trailing ===END===, whitespace around name, content whitespace stripping, internal newlines preserved, markdown preserved, preamble text before first marker ignored), and error case (no markers raises ValueError), and exclusion case (empty-content files excluded).

**File**: `server/modules/chain/tests/test_file_parser.py` (new)

See Section 5 for complete test bodies.

**Verify**:
```bash
python -m pytest modules/chain/tests/test_file_parser.py -v    # expect 11 passed
```

---

### Step 9: Write braindump-to-docs chain tests

**Action**: Create `test_braindump_to_docs.py` with 14 tests covering: definition loading (5 tests: loads, step 1 shape, step 2 shape, step 3 shape, output mode), context block resolution (6 tests: all blocks exist, lint block content, generation block content, rubric content, builder content, principles content), and structural invariants (3 tests: valid JSON, context names in manifest, ops in STEP_HANDLERS).

**File**: `server/modules/chain/tests/test_braindump_to_docs.py` (new)

See Section 5 for complete test bodies.

**Verify**:
```bash
python -m pytest modules/chain/tests/test_braindump_to_docs.py -v    # expect 14 passed
```

---

### Step 10: Run full suite, record delta

**Action**: Run the complete server test suite and confirm zero regressions.

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -m pytest -q
```

**Expected**: baseline + 25 new tests passing. Zero previously-passing tests fail.

---

## 5. Tests

Repo convention: pytest with plain `assert`. Test names use `condition_expectedOutcome` format. Mock provider forced via `conftest.py` in `modules/chain/tests/`.

### File parser tests (`server/modules/chain/tests/test_file_parser.py`)

```python
"""Unit tests for the ===FILE: {name}=== marker parser."""
from __future__ import annotations

import pytest

from modules.chain.file_parser import parse_file_markers


def test_parseFileMarkers_twoFiles_returnsBoth():
    text = """===FILE: a.md===
Content A

===FILE: b.md===
Content B
"""
    files = parse_file_markers(text)
    assert len(files) == 2
    assert files[0]["name"] == "a.md"
    assert "Content A" in files[0]["content"]
    assert files[1]["name"] == "b.md"
    assert "Content B" in files[1]["content"]


def test_parseFileMarkers_fiveFiles_returnsAllInOrder():
    text = "\n".join(
        f"===FILE: file{i}.md===\nContent for file {i}\n" for i in range(1, 6)
    )
    files = parse_file_markers(text)
    assert len(files) == 5
    assert [f["name"] for f in files] == [f"file{i}.md" for i in range(1, 6)]


def test_parseFileMarkers_trailingEndMarker_stripped():
    text = """===FILE: only.md===
Some content

===END==="""
    files = parse_file_markers(text)
    assert len(files) == 1
    assert files[0]["name"] == "only.md"
    assert "===END===" not in files[0]["content"]


def test_parseFileMarkers_noMarkers_raisesValueError():
    with pytest.raises(ValueError, match="No ===FILE:"):
        parse_file_markers("Just plain text without markers.")


def test_parseFileMarkers_emptyContentFile_excluded():
    text = """===FILE: has-content.md===
Real content here.

===FILE: empty.md===

===FILE: also-has-content.md===
More content.
"""
    files = parse_file_markers(text)
    names = [f["name"] for f in files]
    assert "has-content.md" in names
    assert "also-has-content.md" in names
    assert "empty.md" not in names, "files with empty content must be excluded"


def test_parseFileMarkers_whitespaceAroundName_trimmed():
    text = """===FILE:   spaced.md   ===
Content here.
"""
    files = parse_file_markers(text)
    assert files[0]["name"] == "spaced.md"


def test_parseFileMarkers_contentWhitespace_stripped():
    text = """===FILE: trimmed.md===

  Leading and trailing whitespace.

"""
    files = parse_file_markers(text)
    assert files[0]["content"] == "Leading and trailing whitespace."


def test_parseFileMarkers_preservesInternalNewlines():
    text = """===FILE: multi-line.md===
Line 1.

Line 3 after blank.

Line 5.
"""
    files = parse_file_markers(text)
    assert "\n" in files[0]["content"], "internal newlines must be preserved"
    assert "Line 1." in files[0]["content"]
    assert "Line 5." in files[0]["content"]


def test_parseFileMarkers_markdownContentPreserved():
    text = """===FILE: doc.md===
# Heading

## Subheading

- bullet 1
- bullet 2

| Col | Val |
|-----|-----|
| a   | b   |
"""
    files = parse_file_markers(text)
    assert "# Heading" in files[0]["content"]
    assert "| Col | Val |" in files[0]["content"]


def test_parseFileMarkers_textBeforeFirstMarker_ignored():
    text = """Some preamble text the LLM might produce.

===FILE: actual.md===
The real content.
"""
    files = parse_file_markers(text)
    assert len(files) == 1
    assert files[0]["name"] == "actual.md"
    assert "preamble" not in files[0]["content"]


def test_parseFileMarkers_multipleEndMarkers_allStripped():
    text = """===FILE: first.md===
Content one.

===END===

===FILE: second.md===
Content two.

===END==="""
    files = parse_file_markers(text)
    assert len(files) == 2
    for f in files:
        assert "===END===" not in f["content"]
```

### Braindump-to-docs chain tests (`server/modules/chain/tests/test_braindump_to_docs.py`)

```python
"""End-to-end tests for the braindump-to-docs chain definition.

Validates: definition loads, 3 steps configured correctly, context blocks
resolve from manifest, outputMode is multi-file.

Note: mock provider returns deterministic strings, not real multi-file
output with ===FILE:=== markers. The file_parser tests (test_file_parser.py)
cover marker parsing independently. These tests verify the chain
definition shape and context resolution.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from modules.chain.definition_runner import load_definition


# -- Definition loading -------------------------------------------------------

def test_braindumpToDocs_definitionLoads_hasThreeSteps():
    defn = load_definition("braindump-to-docs")
    assert defn.id == "braindump-to-docs"
    assert len(defn.steps) == 3


def test_braindumpToDocs_step1IsReviewLint():
    defn = load_definition("braindump-to-docs")
    step = defn.steps[0]
    assert step.op == "review"
    assert "braindump-lint" in step.context
    assert step.output_key == "lint"


def test_braindumpToDocs_step2IsGenerateWithMultipleContextBlocks():
    defn = load_definition("braindump-to-docs")
    step = defn.steps[1]
    assert step.op == "generate"
    assert "builder" in step.context
    assert "principles" in step.context
    assert "braindump-to-docs" in step.context


def test_braindumpToDocs_step3IsReviewScore():
    defn = load_definition("braindump-to-docs")
    step = defn.steps[2]
    assert step.op == "review"
    assert "quality-rubric" in step.context
    assert step.output_key == "score"


def test_braindumpToDocs_outputModeIsMultiFile():
    defn = load_definition("braindump-to-docs")
    assert defn.output_mode == "multi-file"


# -- Context block resolution -------------------------------------------------

def test_braindumpToDocs_allContextBlocksExistInManifest():
    """Every context block referenced in the definition must resolve."""
    from modules.context.loader import load_block
    defn = load_definition("braindump-to-docs")
    for step in defn.steps:
        for block_name in step.context:
            content = load_block(block_name)
            assert len(content) > 0, f"context block '{block_name}' is empty"


def test_braindumpToDocs_lintBlockContainsReadinessInstructions():
    from modules.context.loader import load_block
    content = load_block("braindump-lint")
    assert "readiness" in content.lower(), "lint block should mention readiness assessment"


def test_braindumpToDocs_generationBlockContainsFileMarkers():
    from modules.context.loader import load_block
    content = load_block("braindump-to-docs")
    assert "===FILE:" in content, "generation block must contain ===FILE: markers as template"


def test_braindumpToDocs_qualityRubricBlockContainsDimensions():
    from modules.context.loader import load_block
    content = load_block("quality-rubric")
    assert "STRUCTURAL COMPLETENESS" in content or "structural_completeness" in content


def test_braindumpToDocs_builderBlockContainsStackInfo():
    from modules.context.loader import load_block
    content = load_block("builder")
    assert "Flask" in content or "Angular" in content, (
        "builder block should mention the primary stack"
    )


def test_braindumpToDocs_principlesBlockContainsPatterns():
    from modules.context.loader import load_block
    content = load_block("principles")
    assert "Adapter" in content or "adapter" in content, (
        "principles block should mention the Adapter pattern"
    )


# -- Structural invariants ----------------------------------------------------

def test_braindumpToDocs_definitionFileIsValidJSON():
    defn_path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "definitions"
        / "braindump-to-docs.json"
    )
    with open(defn_path) as f:
        data = json.load(f)
    assert "id" in data
    assert "steps" in data
    assert "outputMode" in data


def test_braindumpToDocs_contextBlockNamesMatchManifest():
    """Every context block referenced in the definition must exist in manifest.json."""
    defn_path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "definitions"
        / "braindump-to-docs.json"
    )
    manifest_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent.parent
        / "context"
        / "manifest.json"
    )

    with open(defn_path) as f:
        defn = json.load(f)
    with open(manifest_path) as f:
        manifest = json.load(f)

    for step in defn["steps"]:
        for block_name in step.get("context", []):
            assert block_name in manifest, (
                f"context block '{block_name}' referenced in braindump-to-docs.json "
                f"not found in manifest.json. Available: {sorted(manifest.keys())}"
            )


def test_braindumpToDocs_allOpsExistInStepHandlers():
    """Every op referenced in the definition must be a key in STEP_HANDLERS."""
    from modules.chain.definition_runner import STEP_HANDLERS
    defn = load_definition("braindump-to-docs")
    for step in defn.steps:
        assert step.op in STEP_HANDLERS, (
            f"op '{step.op}' in braindump-to-docs.json not found in "
            f"STEP_HANDLERS. Available: {sorted(STEP_HANDLERS.keys())}"
        )
```

**Note on mock mode**: If Task 1's loader mock mode is active (via `CONTEXT_PROVIDER=mock` in `conftest.py`), the context-content assertions (e.g., "lint block should mention readiness") will match mock fixture strings. If mock fixtures for the new block names already exist (Task 1 spec lists them in mock fixtures: `"braindump-lint": "MOCK_CONTEXT[braindump-lint]: check structure"`), these tests will pass but check mock content, not real content. If the executor needs to verify real file content, run those specific tests with `CONTEXT_PROVIDER=file` or unset.

**Adaptation**: If `load_definition` returns a dict instead of a dataclass, change `defn.steps` to `defn["steps"]`, `step.op` to `step["op"]`, etc. The structural invariant tests use `json.load` directly and don't depend on the runner's return type.

---

## 6. Commit Plan

One commit per logical unit. Conventional-commits style.

1. `feat(context): add braindump chain context files + quality rubric` — `server/context/prompts/braindump-lint.md`, `server/context/prompts/braindump-to-docs.md`, `server/context/prompts/builder.md`, `server/context/prompts/principles.md`, `server/context/prompts/references.md`, `server/context/rubrics/quality.md`, `server/context/manifest.json` (modify): six context files for the braindump-to-docs chain. Lint prompt ported from spec-doc/server.js:1142-1189. Generation prompt ported from spec-doc/server.js:718-998. Quality rubric ported from spec-doc/server.js:1023-1084. Builder and principles trimmed from spec-doc/builder.md and principles.md.

2. `feat(chain): add file-marker parser for multi-file output` — `server/modules/chain/file_parser.py`: `parse_file_markers(text)` splits `===FILE: {name}===` delimited LLM output into structured `[{name, content}]`. Anti-corruption layer per architecture doc. Ported from spec-doc's generate-spec marker convention.

3. `feat(chain): wire multi-file parsing into runner + add braindump-to-docs definition` — `server/modules/chain/definition_runner.py` (modify): runner calls `parse_file_markers` when `output_mode == "multi-file"`. `server/modules/chain/definitions/braindump-to-docs.json` (new): 3-step chain (review/lint → generate → review/score).

4. `test(chain): cover file-parser + braindump-to-docs chain` — `server/modules/chain/tests/test_file_parser.py` (11 tests), `server/modules/chain/tests/test_braindump_to_docs.py` (14 tests): marker parsing edge cases, definition shape, context resolution, structural invariants.

**Deviation logging**: if any step is merged with another or the implementation diverges from this guide, prefix the commit body with `Deviations:` and one line per deviation explaining the change.

---

## 7. Verification

```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -m pytest -q
```

**Expected test-count delta**: baseline + **25** new passing tests (11 from `test_file_parser.py` + 14 from `test_braindump_to_docs.py`).

**Zero previously-passing tests broken.** If any test in `server/tests/` or `server/modules/*/tests/` that passed at baseline now fails, STOP and investigate before committing.

Spot-check the file parser:
```bash
python -c "
from modules.chain.file_parser import parse_file_markers
sample = '===FILE: a.md===\nContent A\n===FILE: b.md===\nContent B\n===END==='
files = parse_file_markers(sample)
assert len(files) == 2
print(f'{len(files)} files parsed: {[f[\"name\"] for f in files]}')
"
```

Spot-check the definition loads:
```bash
python -c "
from modules.chain.definition_runner import load_definition
d = load_definition('braindump-to-docs')
print(f'Chain: {d.name}, steps: {len(d.steps)}, output: {d.output_mode}')
"
```

---

## 8. Rollback

**Per-step** (revert in reverse commit order):
- **Commit 4** (tests): `git revert <sha>` — removes test files only, no functional impact.
- **Commit 3** (runner + definition): `git revert <sha>` — removes `braindump-to-docs.json`, reverts runner's multi-file parsing. If other multi-file chains depend on the parser wiring, they break — check before reverting.
- **Commit 2** (file parser): `git revert <sha>` — removes `file_parser.py`. If commit 3 was already reverted, no dangling imports. If not, commit 3 will fail at import.
- **Commit 1** (context files + manifest): `git revert <sha>` — removes 6 context files, reverts manifest entries. If other tasks added manifest entries concurrently (Task 3 adds humanize-pass-1/2/3), use targeted `git checkout <pre-sha> -- server/context/manifest.json` and manually re-add non-braindump entries.

**Per-branch**: `git reset --hard $(cat /tmp/bubls-task4-sha)` restores the pre-task anchor. [REQUIRES APPROVAL]

**No database rollback needed**: this task creates no migrations.

---

## 9. Deviations Allowed

- **`definition_runner` named `runner` instead** — Task 2 may have named the module `runner.py` instead of `definition_runner.py`. Adapt all imports (`from modules.chain.runner import ...`). The key symbols are: `load_definition`, `run_definition`, `STEP_HANDLERS`, `ChainRunResult`. Log as deviation if the name differs.
- **`ChainRunResult` is a dict, not a dataclass** — Task 2 may return dicts from `run_definition`. Adapt the multi-file wiring in Step 6 and the test assertions in Step 9 (use `d["steps"]` instead of `d.steps`). The key invariant: multi-file output goes through `parse_file_markers` and the result has `files` as a list of `{name, content}` dicts.
- **`STEP_HANDLERS` includes additional ops beyond `rewrite`/`generate`/`review`** — fine, this task only uses those three. Do not remove extras.
- **Context loader mock mode active in tests** — if Task 1's `conftest.py` forces `CONTEXT_PROVIDER=mock`, the content assertions (e.g., "lint block should mention readiness") will match mock fixture strings, not real file content. If mock fixtures for `braindump-lint`, `builder`, etc. already exist in the loader, the tests pass against mock content. This is acceptable for CI. To verify real content, run with `CONTEXT_PROVIDER=file` locally.
- **Manifest has different schema than flat `{name: path}`** — adapt entries to match whatever Task 1 implemented. Log in commit body.
- **`rubrics/` directory does not exist** — create it with `mkdir -p server/context/rubrics/`. Note in commit body.
- **Runner already has multi-file parsing from Task 2** — if Task 2 pre-built `parse_file_markers` or equivalent, skip commit 2 and the runner modification in commit 3. Use the existing parser. Log as `Deviations: file_parser already present from Task 2`.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log the deviation in the commit body.

---

## 10. Out of Scope

This task builds the chain definition, context files, and multi-file parser. It does NOT build the frontend rendering, streaming, or retry logic. The executor must STOP and flag (not silently implement) any of the following:

- **Frontend tabbed output** — zero Angular work in Task 4. The tabbed multi-file UI that renders `{files: [...]}` is Task 6.
- **Streaming per chain step** — request-response for v1. SSE is deferred per the architecture doc's design decisions. If the braindump chain feels slow (3 sequential LLM calls), that is expected.
- **Retry on lint failure** — if the lint step returns `"needs_rewrite"`, the chain still proceeds to generation. Automatic retry or user-facing "fix your braindump" flow is a future enhancement (trigger: when users report bad output traceable to bad braindumps).
- **User-editable context blocks** — context files are static markdown checked into the repo. User editing is v2 per the epic's Non-Goals.
- **Custom chain composition** — the braindump chain is a fixed 3-step definition. No user-configurable step ordering.
- **Prompt quality iteration** — port the prompts from spec-doc, verify they produce structurally correct output, stop. Quality refinement is a follow-up based on usage data.
- **Cost tracking / token counting** — deferred. The `chainCompleted` observer event carries token counts, but this task does not build cost analytics dashboards.
- **Alembic migration** — this task adds no database columns. The `chain_id` + `step_count` columns on `superapp_generations` were added by Task 2's migration.
- **Editing `server/modules/context/loader.py`** — if the loader fails on the new entries, that is a Task 1 gap. Flag it, do not fix it here.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — multi-file output design, anti-corruption layer, context loader interface
- [Epic](./epic.md) — Task 4 scope and success criteria
- [Timeline](./timeline.md) — update status to `done` after Verification (Section 7) passes
##### Post-generation review (pipeline)
Strip preamble lines 1-2 (LLM reasoning). definition_runner.py and ChainRunResult are Task 2 symbols — pre-flight must abort if not importable. signals.py referenced but does not exist yet (Task 2). Add mkdir -p server/context/prompts/ alongside rubrics. file_parser.py ACL is well-designed.
