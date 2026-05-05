# Task 4: Braindump to Docs Chain

**Purpose**: Port spec-doc's multi-file generation pipeline into a chain definition with three steps (lint, generate, review), create the supporting context files, implement file-marker parsing in the runner for `outputMode: "multi-file"`, and verify the full flow produces structured `{files: [{name, content}]}` output.

**Effort**: 1 day

**Dependencies**: Task 1 (Context Block Loader), Task 2 (Chain Definition Schema + Runner). Both must be merged. The loader provides `load_block(name)` / `load_blocks(names)`. The runner provides `STEP_HANDLERS` dispatch with `rewrite`, `generate`, and `review` handlers, `load_definition(chainId)`, and the `POST /api/text/chain` endpoint.

**Parallel With**: Task 3 (Deep Humanize) and Task 5 (Rewrite + Review) can run concurrently.

**Blocks**: Task 6 (Chain Mode UI) -- specifically the tabbed output area, which needs a chain that returns `files` to render.

**Related**:
- [Epic](./epic.md) -- Task 4 scope
- [Architecture](./architecture.md) -- multi-file output via `===FILE:===` markers, anti-corruption layer
- `spec-doc/server.js:706-998` -- port source (generate-spec prompt template with `===FILE:===` markers)
- `spec-doc/server.js:1142-1189` -- port source (braindump-lint prompt)

---

## 1. Context

Spec-doc's `generate-spec` endpoint accepts a braindump and produces 5 linked markdown files (spec-index, analysis, epic, architecture, timeline) in a single LLM call, delimited by `===FILE: {name}===` markers. The frontend parses those markers and renders each file in a tab. This is the differentiator -- no competitor ships multi-file generation from a braindump. Porting it to Bubls means: (1) extracting the generation prompt into a context file, (2) extracting the braindump-lint prompt into a separate context file for the pre-flight step, (3) referencing the existing quality rubric for the review step, and (4) teaching the chain runner to parse `===FILE:===` markers when `outputMode` is `"multi-file"`. The marker-parsing is an anti-corruption layer: LLM output format (marker-delimited text) is parsed server-side into structured `[{name, content}]` objects before reaching the frontend.

This task has one code change beyond data files: adding the `parse_file_markers` function to the runner (or a helper module within `chain/`) and wiring it into the runner's response path for `multi-file` definitions. Everything else is data: 4 context files, 1 chain definition JSON, and manifest entries.

**Trade-offs considered**:
- **Multiple LLM calls per file** (one call per doc type) -- rejected: spec-doc's single-call approach is proven, cheaper (1 call vs. 5), and produces internally consistent cross-references between docs. The architecture doc confirms this choice.
- **Structured JSON output from the LLM** -- rejected: Claude is less reliable at producing valid JSON for long-form content (4000+ tokens). Marker-delimited plain text with server-side parsing is the proven pattern from spec-doc.
- **File-marker parsing in the route layer vs. the runner** -- chosen: runner parses markers because `outputMode` is a chain-definition concern, not a route concern. The route returns the runner's structured output directly. This keeps the anti-corruption layer at the right boundary.

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
python -c "from modules.chain.runner import load_definition, STEP_HANDLERS; print('runner ok')"

# Review handler exists in STEP_HANDLERS
python -c "from modules.chain.runner import STEP_HANDLERS; assert 'review' in STEP_HANDLERS; assert 'generate' in STEP_HANDLERS; print('handlers ok')"
```

Confirm the context and definitions directories exist:

```bash
ls server/context/manifest.json
ls server/context/prompts/
ls server/context/rubrics/ || echo "rubrics/ not yet created -- Step 1 will create it"
ls server/modules/chain/definitions/
```

**If any of the above fail**: Task 1 or Task 2 is not merged. STOP.

**Baseline recorded**: [write the pytest pass count into the first commit body].

---

## 3. Files

### To Create (new)

- `server/context/prompts/braindump-lint.md` -- structural pre-flight lint prompt ported from `spec-doc/server.js:1142-1189`
- `server/context/prompts/braindump-to-docs.md` -- multi-file generation prompt ported from `spec-doc/server.js:718-998`, adapted for the Bubls chain runner's `===FILE: {name}===` marker format
- `server/context/prompts/builder.md` -- builder profile context block (content from `spec-doc/builder.md`, trimmed to the sections relevant for generation)
- `server/context/prompts/principles.md` -- architecture principles context block (content from `spec-doc/principles.md`, trimmed to the patterns-to-apply section)
- `server/context/rubrics/quality.md` -- quality rubric for the review step (6-dimension scoring rubric ported from `spec-doc/server.js:1023-1100`)
- `server/modules/chain/definitions/braindump-to-docs.json` -- chain definition with 3 steps (review/lint, generate, review/score)
- `server/modules/chain/file_parser.py` -- `parse_file_markers(text: str) -> list[dict[str, str]]` function that splits `===FILE: {name}===` delimited text into `[{"name": str, "content": str}]`
- `server/modules/chain/tests/test_file_parser.py` -- unit tests for the file-marker parser
- `server/modules/chain/tests/test_braindump_to_docs.py` -- end-to-end chain tests

### To Modify

- `server/context/manifest.json` -- add entries for `braindump-lint`, `braindump-to-docs`, `builder`, `principles`, `quality-rubric`
- `server/modules/chain/runner.py` -- import and call `parse_file_markers` when `definition.outputMode == "multi-file"` before returning the result
- `server/modules/chain/__init__.py` -- optionally re-export `parse_file_markers` if other modules need it (otherwise leave alone)

### To Leave Alone

- `server/modules/text/**` -- braindump chain goes through `/api/text/chain`, not `/api/text/generate`
- `server/modules/chain/adapter.py` -- no changes; chain steps call adapter through STEP_HANDLERS
- `server/modules/chain/providers/**` -- no changes
- `server/modules/context/loader.py` -- no changes; this task only adds files the loader reads
- `src/app/**` -- zero frontend work in Task 4. Tabbed output is Task 6
- `server/app.py` -- no new blueprints; chain endpoint already registered by Task 2

---

## 4. Implementation Steps

### Step 1: Create the braindump-lint context file

**Action**: Port the braindump lint prompt from `spec-doc/server.js:buildBraindumpLintPrompt` (lines 1142-1189) into a standalone markdown file. The prompt instructs the LLM to review a braindump for structural completeness and return JSON with readiness assessment, flags, and fixes. Adapt the prompt to be self-contained (no template variables like `${principles}` -- the runner injects context blocks separately).

**File**: `server/context/prompts/braindump-lint.md` (new)

**Pattern**:
```markdown
You are a structural reviewer for braindumps that will feed a spec-generation pipeline.
Your job: flag gaps that will produce a bad epic + bad tasks. Do NOT rewrite the braindump. Do NOT judge ideas on merit -- only on shape and structural completeness.

Review the braindump against these dimensions:

1. **port_sources**: If the braindump uses words like "port", "copy", "mirror", "adapt from", does it cite specific files? If no port language, pass=true (N/A).
2. **out_of_scope_explicit**: Does the braindump name what it DOES NOT cover and why?
3. **invents_vs_cites**: Does the braindump propose new abstractions without naming a current consumer for each?
4. **consumers_named**: Does every proposed feature or component have a named user or caller?
5. **principles_contradicted**: Does the braindump propose things that contradict the injected PRINCIPLES block?

Return ONLY valid JSON with this exact shape:

{
  "readiness": "ready" | "needs_rewrite" | "ready_with_caveats",
  "flags": [
    { "dim": "port_sources", "pass": true/false, "note": "max 100 chars" },
    { "dim": "out_of_scope_explicit", "pass": true/false, "note": "..." },
    { "dim": "invents_vs_cites", "pass": true/false, "note": "..." },
    { "dim": "consumers_named", "pass": true/false, "note": "..." },
    { "dim": "principles_contradicted", "pass": true/false, "note": "..." }
  ],
  "top_3_fixes": ["...", "...", "..."]
}

Readiness: "ready" = all 5 pass. "ready_with_caveats" = 3-4 pass. "needs_rewrite" = 2+ fail.

Return ONLY the JSON object. No preamble, no prose.
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
wc -l context/prompts/braindump-lint.md    # expect 20-35 lines
head -3 context/prompts/braindump-lint.md   # should start with "You are a structural reviewer"
```

### Step 2: Create the braindump-to-docs generation context file

**Action**: Port the multi-file generation prompt from `spec-doc/server.js:718-998`. This is the core prompt that takes a braindump and produces 5 linked spec files. Key adaptation: replace `${builderProfile}` and `${principles}` template variables with a note that those are injected by the chain runner as separate context blocks. Keep the `===FILE: {name}===` marker format exactly as spec-doc uses it.

**File**: `server/context/prompts/braindump-to-docs.md` (new)

**Pattern**:
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

# [Capability Name] -- Analysis

**Purpose**: Identify problems driving this capability.

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

# [Capability Name] -- Epic

**Purpose**: Define scope and tasks for [capability].

---

## Business Value

2-3 paragraphs on why this matters.

---

## Scope

### What This Epic Covers
- Item 1
- Item 2

### What This Epic Does NOT Cover
- Exclusion 1
- Exclusion 2

---

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **[Task]** | None | -- | 1 day | High |

### Task Details

#### Task 1: [Task Name]
Brief description.

---

## Success Criteria

- Criterion 1
- Criterion 2

---

## Non-Goals

- Non-goal 1

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===FILE: architecture.md===
---
sidebar_position: 3
---

# [Capability Name] -- Architecture

**Purpose**: Technical design for [capability].

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| [Principle] | How it applies |

---

## Component Design

### [Component Name]
Purpose, files, patterns.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Decision] | [Choice] | [Why] |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

===FILE: timeline.md===
---
sidebar_position: 4
---

# [Capability Name] -- Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | [Task] | backlog | |

---

## Status Legend

- backlog - Not started
- in_progress - Currently working
- done - Completed
- blocked - Waiting on dependency

===END===

Generate ALL 5 files with COMPLETE, detailed content based on the user's input.
- Each file should be substantial (300+ words)
- Tasks should be specific and actionable
- Architecture should include real technical details
- Be specific to the user's input, not generic
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
grep "===FILE:" context/prompts/braindump-to-docs.md | wc -l   # expect 5
grep "===END===" context/prompts/braindump-to-docs.md           # expect 1 match
```

### Step 3: Create supporting context files (builder, principles, quality rubric)

**Action**: Create the builder profile, principles, and quality rubric context files. The builder and principles files contain the relevant content from `spec-doc/builder.md` and `spec-doc/principles.md` respectively. The quality rubric contains the 6-dimension scoring model from spec-doc's review endpoint.

**File**: `server/context/prompts/builder.md` (new), `server/context/prompts/principles.md` (new), `server/context/rubrics/quality.md` (new)

**Pattern** for `server/context/rubrics/quality.md`:
```markdown
Score each dimension 1-5 and list specific violations.

## 1. STRUCTURAL COMPLETENESS
Are all required sections present for each document type?
- Analysis: Summary, Issue Breakdown, Related Docs
- Epic: Business Value, Scope (in/out), Task Table, Success Criteria, Non-Goals
- Architecture: Design Principles, Component Design, Design Decisions

## 2. CONTENT ROUTING COMPLIANCE
Is content in the RIGHT document?
- Status words in Epic or Architecture? VIOLATION
- Design decisions in Epic? VIOLATION
- Business value in Architecture? VIOLATION

## 3. CROSS-REFERENCE INTEGRITY
Do documents reference each other correctly?
- Every doc should have a Related Documents section
- Links should point to sibling files (./epic.md, ./architecture.md)

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

Return JSON:
{
  "dimensions": [
    { "name": "structural_completeness", "score": 1-5, "violations": ["..."] },
    { "name": "content_routing", "score": 1-5, "violations": ["..."] },
    { "name": "cross_references", "score": 1-5, "violations": ["..."] },
    { "name": "task_specificity", "score": 1-5, "violations": ["..."] },
    { "name": "scope_discipline", "score": 1-5, "violations": ["..."] },
    { "name": "technical_depth", "score": 1-5, "violations": ["..."] }
  ],
  "overall_score": 1-5,
  "summary": "one sentence"
}
```

**Pattern** for `server/context/prompts/builder.md`:
```markdown
## Builder Context

- Role: Full-stack developer, solo founder building SaaS products
- Style: Minimal, ship fast, validate before expanding
- Primary Stack: Angular 19 + Ionic 8 + Flask + Neon Postgres
- AI: Claude API (Anthropic) for generation/curation
- Deployment: Coolify + Docker Compose + GitHub Actions
- Auth: Neon Postgres only. Magic link tokens. Never Supabase, never Firebase
- Pattern: Ship in < 1 week, validate with 200 users, iterate from signal

Use this context to inform technology choices and architecture decisions.
```

**Pattern** for `server/context/prompts/principles.md`:
```markdown
## Architecture Principles (non-negotiable)

- Feature = Bounded Context: each feature is a lazy-loaded route with own models, service, mock, tests
- Adapter: every service adapts between UI and backend; mock mode via env flag
- Strategy: each feature declares which AI backend it needs; swap without touching UI
- Registry: user.enabled_features array for per-user gating
- Observer: features publish signals/events; never import each other
- Anti-Corruption Layer: mapper isolates domain from external API response formats
- Standalone Components, OnPush, Signals: no NgModules
- Flask Minimal: ~30 lines per endpoint; factory pattern
- OpenAPI-First: generate DTOs from YAML spec
- Always ORM, Never Raw SQL: SQLAlchemy/SQLModel for all DB access
- data-test selectors only in tests

The architecture document MUST follow these principles.
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
ls context/prompts/builder.md context/prompts/principles.md context/rubrics/quality.md
wc -l context/rubrics/quality.md    # expect 40-60 lines
```

### Step 4: Register all new context blocks in the manifest

**Action**: Add entries for `braindump-lint`, `braindump-to-docs`, `builder`, `principles`, `quality-rubric` to `server/context/manifest.json`. If entries from Task 3 already exist, merge without overwriting.

**File**: `server/context/manifest.json` (modify)

**Pattern** (final manifest should include at minimum these entries):
```json
{
  "braindump-lint": "prompts/braindump-lint.md",
  "braindump-to-docs": "prompts/braindump-to-docs.md",
  "builder": "prompts/builder.md",
  "principles": "prompts/principles.md",
  "quality-rubric": "rubrics/quality.md"
}
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -c "
from modules.context.loader import load_blocks
blocks = load_blocks(['braindump-lint', 'braindump-to-docs', 'builder', 'principles', 'quality-rubric'])
for name, content in blocks.items():
    assert len(content) > 0, f'{name} is empty'
    print(f'{name}: {len(content)} chars')
print('all 5 blocks loaded ok')
"
```

### Step 5: Implement the file-marker parser

**Action**: Create `server/modules/chain/file_parser.py` with a `parse_file_markers(text: str) -> list[dict[str, str]]` function. The parser splits text on `===FILE: {name}===` markers, strips any trailing `===END===` marker, and returns a list of `{"name": filename, "content": content}` dicts. Content is stripped of leading/trailing whitespace. Files with empty content after stripping are excluded.

**File**: `server/modules/chain/file_parser.py` (new)

**Pattern**:
```python
# server/modules/chain/file_parser.py
"""Anti-corruption layer: parse ===FILE: {name}=== markers from LLM output.

LLM multi-file output is a single string with marker-delimited sections.
This parser converts it to structured [{name, content}] before the response
reaches the frontend. The LLM output format never leaks past this boundary.

Ported from spec-doc/server.js generate-spec endpoint, which uses the same
===FILE: {name}=== / ===END=== marker convention.
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
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -c "
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

### Step 6: Wire file-marker parsing into the runner for multi-file output

**Action**: Modify `server/modules/chain/runner.py` to import `parse_file_markers` and call it when `definition["outputMode"] == "multi-file"`. The runner's `run_definition` return value changes shape: for `single` mode it returns `{"result": str}`, for `multi-file` mode it returns `{"files": [{name, content}]}`. This is the anti-corruption layer described in the architecture doc.

**File**: `server/modules/chain/runner.py` (modify)

**Pattern** (add to the `run_definition` function's return path):
```python
from .file_parser import parse_file_markers

# Inside run_definition, after the final step produces output:
if definition.get("outputMode") == "multi-file":
    files = parse_file_markers(final_output)
    return {"files": files}
else:
    return {"result": final_output}
```

The exact insertion point depends on Task 2's `run_definition` implementation. The key invariant: `parse_file_markers` is called on the raw LLM output string, and its structured return replaces the raw string in the response.

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -c "
from modules.chain.file_parser import parse_file_markers
from modules.chain.runner import run_definition
# Verify the import chain works
print('import ok')
"
```

### Step 7: Create the braindump-to-docs chain definition

**Action**: Create the chain definition JSON with 3 steps: (1) review/lint the braindump, (2) generate multi-file output with builder+principles+references context, (3) review the output against the quality rubric.

**File**: `server/modules/chain/definitions/braindump-to-docs.json` (new)

**Pattern**:
```json
{
  "id": "braindump-to-docs",
  "name": "Brain Dump \u2192 Docs",
  "steps": [
    { "op": "review", "context": ["braindump-lint"], "outputKey": "lint" },
    { "op": "generate", "context": ["builder", "principles", "braindump-to-docs"] },
    { "op": "review", "context": ["quality-rubric"], "outputKey": "score" }
  ],
  "outputMode": "multi-file"
}
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -c "
import json
with open('modules/chain/definitions/braindump-to-docs.json') as f:
    d = json.load(f)
assert d['id'] == 'braindump-to-docs'
assert len(d['steps']) == 3
assert d['steps'][0]['op'] == 'review'
assert d['steps'][1]['op'] == 'generate'
assert d['steps'][2]['op'] == 'review'
assert d['outputMode'] == 'multi-file'
print('definition valid')
"
```

### Step 8: Write file-parser unit tests

**Action**: Create `test_file_parser.py` with comprehensive tests for the marker parser: happy path, edge cases (empty content, no markers, trailing ===END===, whitespace handling), and error cases.

**File**: `server/modules/chain/tests/test_file_parser.py` (new). See Section 5 for full bodies.

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -m pytest modules/chain/tests/test_file_parser.py -v
```

### Step 9: Write end-to-end chain tests

**Action**: Create `test_braindump_to_docs.py` with tests covering: definition loads, 3 steps execute, context blocks resolve, multi-file output is parsed, structural invariants hold.

**File**: `server/modules/chain/tests/test_braindump_to_docs.py` (new). See Section 5 for full bodies.

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -m pytest modules/chain/tests/test_braindump_to_docs.py -v
```

### Step 10: Run the full suite, record delta

**Action**: Run the complete server test suite and confirm zero regressions.

**File**: none (test execution only)

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -m pytest -q
```

**Expected**: baseline + new tests passing. Zero previously-passing tests fail.

---

## 5. Tests

Repo convention: pytest with plain `assert`. Test names use `condition_expectedOutcome` convention. Mock provider forced via `conftest.py` in `modules/chain/tests/`.

### File parser tests

```python
# server/modules/chain/tests/test_file_parser.py
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
```

### Braindump-to-docs chain tests

```python
# server/modules/chain/tests/test_braindump_to_docs.py
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

from modules.chain.runner import load_definition


# -- Definition loading ------------------------------------------------------

def test_braindumpToDocs_definitionLoads_hasThreeSteps():
    defn = load_definition("braindump-to-docs")
    assert defn["id"] == "braindump-to-docs"
    assert len(defn["steps"]) == 3


def test_braindumpToDocs_step1IsReviewLint():
    defn = load_definition("braindump-to-docs")
    step = defn["steps"][0]
    assert step["op"] == "review"
    assert "braindump-lint" in step["context"]
    assert step.get("outputKey") == "lint"


def test_braindumpToDocs_step2IsGenerateWithMultipleContextBlocks():
    defn = load_definition("braindump-to-docs")
    step = defn["steps"][1]
    assert step["op"] == "generate"
    context_names = step["context"]
    assert "builder" in context_names
    assert "principles" in context_names
    assert "braindump-to-docs" in context_names


def test_braindumpToDocs_step3IsReviewScore():
    defn = load_definition("braindump-to-docs")
    step = defn["steps"][2]
    assert step["op"] == "review"
    assert "quality-rubric" in step["context"]
    assert step.get("outputKey") == "score"


def test_braindumpToDocs_outputModeIsMultiFile():
    defn = load_definition("braindump-to-docs")
    assert defn["outputMode"] == "multi-file"


# -- Context block resolution ------------------------------------------------

def test_braindumpToDocs_allContextBlocksExistInManifest():
    """Every context block referenced in the definition must resolve."""
    from modules.context.loader import load_block
    defn = load_definition("braindump-to-docs")
    for step in defn["steps"]:
        for block_name in step.get("context", []):
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


# -- Structural invariants ---------------------------------------------------

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
    from modules.chain.runner import STEP_HANDLERS
    defn = load_definition("braindump-to-docs")
    for step in defn["steps"]:
        assert step["op"] in STEP_HANDLERS, (
            f"op '{step['op']}' in braindump-to-docs.json not found in "
            f"STEP_HANDLERS. Available: {sorted(STEP_HANDLERS.keys())}"
        )
```

---

## 6. Commit Plan

One commit per logical unit. Conventional-commits style.

1. `feat(chain): add braindump context files (lint, generation, builder, principles, rubric)` -- `server/context/prompts/braindump-lint.md`, `server/context/prompts/braindump-to-docs.md`, `server/context/prompts/builder.md`, `server/context/prompts/principles.md`, `server/context/rubrics/quality.md`, `server/context/manifest.json` (modify): five context files for the braindump-to-docs chain. Lint prompt ported from spec-doc/server.js:1142-1189. Generation prompt ported from spec-doc/server.js:718-998. Quality rubric ported from spec-doc/server.js:1023-1100.

2. `feat(chain): add file-marker parser for multi-file output` -- `server/modules/chain/file_parser.py`: `parse_file_markers(text)` splits `===FILE: {name}===` delimited LLM output into structured `[{name, content}]`. Anti-corruption layer per architecture doc.

3. `feat(chain): wire multi-file parsing into runner + add braindump-to-docs definition` -- `server/modules/chain/runner.py` (modify), `server/modules/chain/definitions/braindump-to-docs.json` (new): runner calls `parse_file_markers` when `outputMode == "multi-file"`. Definition has 3 steps: lint, generate, review.

4. `test(chain): cover file-parser + braindump-to-docs chain` -- `server/modules/chain/tests/test_file_parser.py`, `server/modules/chain/tests/test_braindump_to_docs.py`: 11 parser tests + 14 chain tests covering definition shape, context resolution, structural invariants.

**Deviation logging**: if any step is merged with another, prefix the commit body with `Deviations:` and one line explaining.

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
cd {WORKSPACE}/bubls/server
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
cd {WORKSPACE}/bubls/server
python -c "
from modules.chain.runner import load_definition
d = load_definition('braindump-to-docs')
print(f'Chain: {d[\"name\"]}, steps: {len(d[\"steps\"])}, output: {d[\"outputMode\"]}')
"
```

---

## 8. Rollback

**Per-step** (revert in reverse order):
- Commit 4 (tests): `git revert <sha>` -- removes test files only, no functional impact.
- Commit 3 (runner + definition): `git revert <sha>` -- removes `braindump-to-docs.json`, reverts runner's multi-file parsing. If other multi-file chains depend on the parser wiring, they break. Check before reverting.
- Commit 2 (file parser): `git revert <sha>` -- removes `file_parser.py`. If commit 3 was already reverted, no dangling imports. If not, commit 3 will fail at import.
- Commit 1 (context files + manifest): `git revert <sha>` -- removes 5 context files, reverts manifest entries. If other tasks added manifest entries, use targeted `git checkout <pre-sha> -- server/context/manifest.json` and manually re-add non-braindump entries.

**Per-branch**: `git reset --hard $(cat /tmp/bubls-task4-sha)` restores the pre-task anchor.

**No database rollback needed**: this task creates no migrations.

---

## 9. Deviations Allowed

- **`run_definition` function name or return shape differs from what this spec assumes**: Task 2 may have named it differently or structured the return differently. Adapt the runner modification and test assertions to match Task 2's actual implementation. The key invariants to preserve: (1) multi-file definitions trigger marker parsing, (2) the response contains a `files` list with `name` and `content` keys.
- **`STEP_HANDLERS` includes additional ops beyond `rewrite`/`generate`/`review`**: fine, this task only uses those three. Do not remove extras.
- **Context loader mock mode**: if Task 1's loader has a mock mode that returns fixture strings instead of reading files, and it's active in tests, the context-content assertions (e.g., "lint block should mention readiness") will fail against mock strings. Either disable mock mode for those specific tests or adjust assertions to match the mock fixture.
- **Manifest has a different schema than flat `{name: path}`**: adapt the entries to match whatever Task 1 implemented. Note in the commit body.
- **`rubrics/` directory does not exist**: create it (`mkdir -p server/context/rubrics/`). Note in commit body.
- **Builder/principles content differs from spec-doc originals**: trim or adapt to fit Bubls's context. The content is a starting point; it can be iterated later. The structural shape (file exists, manifest entry resolves, content is non-empty) is the hard constraint.
- **Runner already has file-marker parsing** (Task 2 may have pre-built it): skip commit 2 and the runner modification in commit 3. Note as `Deviations: file_parser already present from Task 2`.

---

## 10. Out of Scope

The executor must STOP and flag (not silently implement) any of the following:

- **Streaming per chain step** -- request-response for v1. SSE is deferred to a future epic. If the braindump chain feels slow (3 LLM calls), that is expected.
- **Frontend tabbed output** -- zero Angular work in Task 4. The tabbed output UI that renders `{files: [...]}` is Task 6.
- **User-editable context blocks** -- context files are static markdown checked into the repo. User editing is v2 per the epic's Non-Goals.
- **Custom chain composition** -- the braindump chain is a fixed 3-step definition. No user-configurable step ordering.
- **Prompt quality iteration** -- port the prompts from spec-doc, verify they produce structurally correct output, stop. Quality refinement is a follow-up based on usage data.
- **References context block** -- the architecture doc shows `"references"` in the braindump-to-docs context list. If the spec-doc references file is too large or too specific to spec-doc, omit it from the chain definition and note the deviation. The chain must work without it.
- **Alembic migration** -- this task adds no database columns.
- **Cost tracking / token counting** -- deferred. The `chainCompleted` observer event (if wired by Task 2) will carry `totalTokens`, but this task does not build cost analytics.
- **Retry on lint failure** -- if the lint step returns `"needs_rewrite"`, the chain still proceeds to generation. Automatic retry or user-facing "fix your braindump" flow is a future enhancement.
- **Editing `server/modules/context/loader.py`** -- if the loader fails on the new entries, that is a Task 1 gap. Flag it, do not fix it here.

---

## Related Documents

- [Epic](./epic.md) -- Task 4 scope and success criteria
- [Architecture](./architecture.md) -- multi-file output design, anti-corruption layer, context loader interface
- [Timeline](./timeline.md) -- update status to Done after Verification (Section 7) passes
