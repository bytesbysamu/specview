The filesystem is read-only and requires a write permission grant that hasn't been provided in this environment. Here is the complete `implementation-guide.md` content, fully ready to save:

---

# Implementation Guide: Thin API Phase 2

> **Audience**: Engineers implementing or reviewing this epic.
> **Scope**: Task-by-task instructions, file layouts, code contracts, and acceptance verification for all four tasks.
> **Companion documents**: [epic.md](./epic.md) · [architecture.md](./architecture.md)

---

## Table of Contents

1. [Prerequisites and Orientation](#1-prerequisites-and-orientation)
2. [Repository Layout After Phase 2](#2-repository-layout-after-phase-2)
3. [Task 1 — Skill Registry Contract](#3-task-1--skill-registry-contract)
4. [Task 2 — Benchmark Runner](#4-task-2--benchmark-runner)
5. [Task 3 — Track A Sync Migration](#5-task-3--track-a-sync-migration)
6. [Task 4 — Track B Async Migration](#6-task-4--track-b-async-migration)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Acceptance Verification Checklist](#8-acceptance-verification-checklist)

---

## 1. Prerequisites and Orientation

### Dependency order

```
Task 1 (Registry Contract)
   +-- Task 2 (Benchmark Runner)   <- starts after Task 1 is merged
   +-- Task 3 (Track A Migration)  <- starts after Task 1 is merged
         +-- Task 4 (Track B Migration) <- starts only after Task 3 clears 95% gate
```

Tasks 2 and 3 may be worked in parallel by different contributors once Task 1 is merged. Task 4 must not begin until the Track A benchmark gate is cleared.

### "Zero AI strings in Python" invariant

Every task in this epic is written with this invariant as a hard constraint. Before opening a PR, run the grep linter locally (see Section 7.1) against every file you touched in `api/modules/ai/`. A failing linter is a build failure.

### Rollback surface

Old per-skill Python routes stay live throughout the migration. Do not delete any existing route until its benchmark gate is cleared **and** a production soak confirms stability. Treat old routes like live code: keep them passing tests and linting until they are retired.

---

## 2. Repository Layout After Phase 2

```
api/
  modules/
    ai/
      routes/
        generic_skill_route.py       # single Flask Blueprint handler (<=200 lines)
        generic_skill_service.py     # business logic delegation (<=200 lines)
        output_validator.py          # JSON Schema enforcement module
        # OLD per-skill routes remain until retirement gate clears
        rewrite_route.py             # retired after Track A gate
        review_route.py              # retired after Track A gate
        brainstorm_route.py          # retired after Track B gate
        spec_pipeline_route.py       # retired after Track B gate
      skills/
        rewrite/
          SKILL.md
          skill.json                 # extended with execution_model + output_schema
        review/
          SKILL.md
          skill.json
        brainstorm/
          SKILL.md
          skill.json
        spec_pipeline/
          SKILL.md
          skill.json
    runtime/
      chain/
        adapter.py                   # unchanged; all AI calls route through here

tools/
  benchmark/
    runner.py                        # entry point; parses CLI args, loads corpus
    corpus_loader.py                 # reads .jobs/<job_id>/run.log files
    evaluators/
      structural.py                  # JSON key/type checks for async pipeline skills
      llm_judge.py                   # LLM-as-judge via chain adapter for prose skills
    rubrics/
      rewrite_rubric.md              # versioned rubric document
      review_rubric.md               # versioned rubric document

.jobs/
  <job_id>/
    run.log                          # corpus entry; written by every skill invocation

ci/
  lint_ai_strings.py                 # grep-based linter; blocks build on violation

openapi.yaml                         # generic skill endpoint declared before implementation
```

---

## 3. Task 1 — Skill Registry Contract

**Goal**: Extend `skill.json` with `execution_model` and `output_schema`; build the generic route that reads both; build the output validator; ensure zero AI strings remain in Python.

**Estimated effort**: 2 days  
**Blocks**: Tasks 2, 3, and 4

### 3.1 Extend skill.json Schema

Add two required top-level fields to every skill's `skill.json`. This schema is the contract every other component depends on — get it right before touching the route.

```jsonc
// api/modules/ai/skills/<skill_name>/skill.json
{
  "name": "rewrite",          // snake_case, matches directory name
  "version": "1.0.0",         // semver; bump on any behavioral change
  "execution_model": "sync",  // "sync" | "async"
  "output_schema": {          // JSON Schema (draft-07) for agent stdout
    "type": "object",
    "required": ["rewritten_text"],
    "properties": {
      "rewritten_text": { "type": "string" }
    },
    "additionalProperties": false
  }
}
```

**Field rules**:

| Field | Value | Behaviour |
|---|---|---|
| `execution_model` | `"sync"` | Route awaits adapter; returns 200 with body + `X-Job-Id` header |
| `execution_model` | `"async"` | Route spawns daemon thread; returns 202 with `job_id` immediately |
| `output_schema` | JSON Schema object | Python validates agent stdout against this schema before any response is written |

**Canonical output schemas** — copy exactly into each `skill.json`:

**rewrite**:
```json
{
  "type": "object",
  "required": ["rewritten_text"],
  "properties": {
    "rewritten_text": { "type": "string" }
  },
  "additionalProperties": false
}
```

**review**:
```json
{
  "type": "object",
  "required": ["feedback"],
  "properties": {
    "feedback": { "type": "string" }
  },
  "additionalProperties": false
}
```

**brainstorm**:
```json
{
  "type": "object",
  "required": ["questions", "recommendations", "rewritten_braindump", "suggested_action"],
  "properties": {
    "questions":           { "type": "array",  "items": { "type": "string" } },
    "recommendations":     { "type": "array",  "items": { "type": "string" } },
    "rewritten_braindump": { "type": "string" },
    "suggested_action":    { "type": ["string", "null"] }
  },
  "additionalProperties": false
}
```

> `suggested_action` **must be present** in every brainstorm response. Its value may be `null` this phase — but the field must never be absent. Frontend must handle `null` gracefully.

**spec_pipeline**:
```json
{
  "type": "object",
  "required": ["pipeline_result"],
  "properties": {
    "pipeline_result": { "type": "object" }
  },
  "additionalProperties": false
}
```

> Refine `pipeline_result` sub-schema once the skill's concrete output shape is characterised during Track B.

### 3.2 Declare the Generic Endpoint in openapi.yaml

Add the endpoint **before** writing any Python. OpenAPI-first (P5) means the contract is reviewable independently of implementation.

```yaml
# openapi.yaml — add under paths:
/skills/{skill_name}/run:
  post:
    operationId: runSkill
    summary: Execute a registered skill by name
    parameters:
      - name: skill_name
        in: path
        required: true
        schema:
          type: string
          enum: [rewrite, review, brainstorm, spec_pipeline]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [input]
            properties:
              input:
                type: string
    responses:
      "200":
        description: Sync skill result
        headers:
          X-Job-Id:
            schema: { type: string }
        content:
          application/json:
            schema:
              type: object
              description: Shape declared by skill output_schema
      "202":
        description: Async skill accepted; poll job_id for result
        content:
          application/json:
            schema:
              type: object
              required: [job_id]
              properties:
                job_id: { type: string }
      "422":
        description: Agent stdout failed output_schema validation
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/SkillError"
```

### 3.3 Build the Output Validator

Create `api/modules/ai/routes/output_validator.py` as a standalone, independently testable module. Do not inline it into the route.

```python
# api/modules/ai/routes/output_validator.py
import json
import jsonschema
from typing import Any


class OutputValidationError(Exception):
    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors


def validate(raw_stdout: str, output_schema: dict) -> Any:
    """
    Parse raw_stdout as JSON and validate against output_schema.
    Returns the parsed object on success.
    Raises OutputValidationError on parse failure or schema violation.
    """
    try:
        data = json.loads(raw_stdout)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(
            "Agent stdout is not valid JSON",
            [str(exc)]
        )

    validator = jsonschema.Draft7Validator(output_schema)
    errors = [e.message for e in validator.iter_errors(data)]
    if errors:
        raise OutputValidationError(
            "Agent stdout does not match declared output_schema",
            errors
        )

    return data
```

**Unit tests to write** in `tests/test_output_validator.py`:

- Valid JSON matching schema → returns parsed dict, no exception raised
- Valid JSON with missing required field → raises `OutputValidationError`
- Non-JSON stdout → raises `OutputValidationError` with parse message
- `additionalProperties: false` violated → raises `OutputValidationError`

### 3.4 Build the Generic Route

`generic_skill_route.py` must stay under 200 lines. All business logic lives in `generic_skill_service.py`.

```python
# api/modules/ai/routes/generic_skill_route.py
import uuid
import threading
from flask import Blueprint, request, jsonify
from .generic_skill_service import (
    load_skill_registry,
    run_sync_skill,
    start_async_skill,
)
from .output_validator import OutputValidationError

skill_bp = Blueprint("skills", __name__, url_prefix="/skills")

# Handler registry — adding a new execution model adds an entry here,
# not a conditional branch. The route never inspects the skill name.
EXECUTION_HANDLERS = {
    "sync":  "_handle_sync",
    "async": "_handle_async",
}


@skill_bp.route("/<skill_name>/run", methods=["POST"])
def run_skill(skill_name: str):
    body = request.get_json(force=True) or {}
    user_input = body.get("input", "")

    try:
        registry = load_skill_registry(skill_name)
    except FileNotFoundError:
        return jsonify({"error": "Skill not found"}), 404

    execution_model = registry["execution_model"]
    handler_name = EXECUTION_HANDLERS.get(execution_model)
    if handler_name is None:
        return jsonify({"error": "Unknown execution_model: " + execution_model}), 500

    return globals()[handler_name](skill_name, user_input, registry)


def _handle_sync(skill_name, user_input, registry):
    job_id = str(uuid.uuid4())
    try:
        result = run_sync_skill(skill_name, user_input, registry, job_id)
    except OutputValidationError as exc:
        return jsonify({"error": exc.args[0], "details": exc.errors}), 422
    response = jsonify(result)
    response.headers["X-Job-Id"] = job_id
    return response, 200


def _handle_async(skill_name, user_input, registry):
    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=start_async_skill,
        args=(skill_name, user_input, registry, job_id),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id}), 202


@skill_bp.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    from api.modules.ai.job_store import job_store
    entry = job_store.get(job_id)
    if entry is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(entry), 200
```

```python
# api/modules/ai/routes/generic_skill_service.py
import json
from pathlib import Path
from .output_validator import validate
from api.modules.runtime.chain.adapter import run_skill_adapter
from api.modules.ai.job_log import write_run_log   # existing module

SKILLS_BASE = Path(__file__).parent.parent / "skills"


def load_skill_registry(skill_name: str) -> dict:
    """Read and return skill.json for the given skill name."""
    path = SKILLS_BASE / skill_name / "skill.json"
    if not path.exists():
        raise FileNotFoundError(skill_name)
    return json.loads(path.read_text())


def run_sync_skill(skill_name, user_input, registry, job_id) -> dict:
    """
    Call the adapter synchronously.
    Validate stdout against output_schema.
    Write run log entry.
    Return the validated, parsed output dict.
    """
    raw_stdout = run_skill_adapter(skill_name, user_input)
    result = validate(raw_stdout, registry["output_schema"])
    write_run_log(job_id, skill_name, user_input, raw_stdout, execution_model="sync")
    return result


def start_async_skill(skill_name, user_input, registry, job_id):
    """
    Called from a daemon thread.
    Call the adapter, validate stdout, write run log.
    Updates the in-process job state dict with result or error.
    """
    from api.modules.ai.job_store import job_store
    job_store[job_id] = {"status": "running"}
    try:
        raw_stdout = run_skill_adapter(skill_name, user_input)
        result = validate(raw_stdout, registry["output_schema"])
        write_run_log(job_id, skill_name, user_input, raw_stdout, execution_model="async")
        job_store[job_id] = {"status": "complete", "result": result}
    except Exception as exc:
        job_store[job_id] = {"status": "error", "error": str(exc)}
```

> **Key invariant**: Neither `generic_skill_route.py` nor `generic_skill_service.py` contains any natural-language instruction string. All prompt content lives in `SKILL.md` files and is loaded by `run_skill_adapter` via the skill directory path.

### 3.5 Register the Blueprint

In `api/app.py` (or wherever blueprints are registered):

```python
from api.modules.ai.routes.generic_skill_route import skill_bp
app.register_blueprint(skill_bp)
```

### 3.6 Task 1 Done — Verify

```bash
# 1. Zero AI strings in Python
python ci/lint_ai_strings.py api/modules/ai/
# Expected: PASS — No AI strings in Python.

# 2. Output validator unit tests pass
pytest tests/test_output_validator.py -v

# 3. Generic route smoke test — sync skill
curl -X POST http://localhost:5000/skills/rewrite/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world"}' -i
# Expected: HTTP 200 + X-Job-Id header

# 4. Generic route smoke test — async skill
curl -X POST http://localhost:5000/skills/brainstorm/run \
  -H "Content-Type: application/json" \
  -d '{"input": "I want to build an app"}' -i
# Expected: HTTP 202 + body containing job_id
```

---

## 4. Task 2 — Benchmark Runner

**Goal**: Build a reproducible, corpus-driven runner that produces a per-track pass/fail verdict. The runner is the confidence machine that gates route retirement.

**Starts after**: Task 1 merged  
**Can run in parallel with**: Task 3  
**Estimated effort**: 2 days

### 4.1 Corpus Loader

```python
# tools/benchmark/corpus_loader.py
import json
from pathlib import Path
from typing import Iterator

JOBS_DIR = Path(".jobs")


def iter_corpus(skill_name: str, n: int = 10) -> Iterator[dict]:
    """
    Yield up to n run.log entries for the given skill.
    Each entry is a dict with keys: job_id, skill_name, input, raw_stdout.
    Curate a seed set of N=10 before migration if organic logs are sparse.
    """
    entries = []
    for log_path in JOBS_DIR.glob("*/run.log"):
        try:
            entry = json.loads(log_path.read_text())
        except (json.JSONDecodeError, IOError):
            continue
        if entry.get("skill_name") == skill_name:
            entries.append(entry)
        if len(entries) >= n:
            break
    return iter(entries)
```

**Seed corpus setup** (manual, one-time per track at migration start):

Create 10 representative job logs for each skill before the first benchmark run. Each log is a JSON file at `.jobs/<uuid>/run.log` in the standard run.log format:

```json
{
  "job_id":          "seed-rewrite-01",
  "skill_name":      "rewrite",
  "input":           "The system is bad and needs to be fixed.",
  "raw_stdout":      "{\"rewritten_text\": \"The system requires remediation.\"}",
  "execution_model": "sync",
  "timestamp_utc":   "2026-05-01T10:00:00Z",
  "schema_valid":    true
}
```

Repeat for all 10 seed entries per track. Use inputs that reflect real user patterns, not synthetic edge cases — the corpus is the test surface.

### 4.2 Structural Evaluator (async pipeline skills)

Used for: `brainstorm`, `spec_pipeline`

```python
# tools/benchmark/evaluators/structural.py
import json
import jsonschema


def evaluate(entry: dict, output_schema: dict) -> dict:
    """
    Validate raw_stdout against output_schema deterministically.
    Returns {"pass": bool, "job_id": str, "reason": str}
    """
    try:
        data = json.loads(entry["raw_stdout"])
    except json.JSONDecodeError as exc:
        return {
            "pass": False,
            "job_id": entry["job_id"],
            "reason": "stdout not valid JSON: " + str(exc),
        }

    validator = jsonschema.Draft7Validator(output_schema)
    errors = [e.message for e in validator.iter_errors(data)]
    if errors:
        return {
            "pass": False,
            "job_id": entry["job_id"],
            "reason": "; ".join(errors),
        }
    return {"pass": True, "job_id": entry["job_id"], "reason": ""}
```

### 4.3 LLM-as-Judge Evaluator (sync prose skills)

Used for: `rewrite`, `review`

```python
# tools/benchmark/evaluators/llm_judge.py
from pathlib import Path
from api.modules.runtime.chain.adapter import run_skill_adapter

RUBRICS_DIR = Path(__file__).parent.parent / "rubrics"


def evaluate(entry: dict, skill_name: str) -> dict:
    """
    Submit agent output and rubric to the chain adapter.
    Returns {"pass": bool, "job_id": str, "reason": str}.
    Ambiguous judge verdicts are treated as conservative fails.
    """
    rubric = (RUBRICS_DIR / (skill_name + "_rubric.md")).read_text()
    judge_input = _build_judge_input(entry["input"], entry["raw_stdout"], rubric)
    raw_verdict = run_skill_adapter("judge", judge_input)

    upper = raw_verdict.upper()
    if "PASS" in upper:
        return {"pass": True,  "job_id": entry["job_id"], "reason": raw_verdict}
    if "FAIL" in upper:
        return {"pass": False, "job_id": entry["job_id"], "reason": raw_verdict}

    # Ambiguous — conservative fail
    return {
        "pass": False,
        "job_id": entry["job_id"],
        "reason": "Ambiguous judge response: " + raw_verdict,
    }


def _build_judge_input(user_input: str, agent_output: str, rubric: str) -> str:
    return (
        "RUBRIC:\n" + rubric + "\n\n"
        "USER INPUT:\n" + user_input + "\n\n"
        "AGENT OUTPUT:\n" + agent_output + "\n\n"
        "Evaluate the agent output against the rubric. "
        "Respond with PASS or FAIL followed by a one-sentence justification."
    )
```

### 4.4 Rubric Documents

Each rubric is a **versioned, checked-in markdown file** — not code, not inline strings. A rubric change invalidates historical pass rates and must be announced explicitly in the PR description as a benchmark reset.

**`tools/benchmark/rubrics/rewrite_rubric.md`** — v1.0:

```markdown
# Rewrite Skill — LLM Judge Rubric  v1.0

## Evaluation Criteria

A rewrite response PASSES if ALL of the following are true:

1. **Preservation** — The rewritten text conveys the same factual content as the input;
   no information is dropped or distorted.
2. **Clarity** — The rewritten text is more clearly expressed than the input:
   shorter, better structured, or less ambiguous.
3. **Format** — The response is a JSON object with exactly one key, `rewritten_text`,
   whose value is a non-empty string.
4. **No hallucination** — The rewritten text does not introduce facts, claims,
   or details not present in the input.

A rewrite response FAILS if ANY criterion above is not met.

## Response format

Respond with exactly: `PASS — <one sentence>` or `FAIL — <one sentence>`.
```

**`tools/benchmark/rubrics/review_rubric.md`** — v1.0:

```markdown
# Review Skill — LLM Judge Rubric  v1.0

## Evaluation Criteria

A review response PASSES if ALL of the following are true:

1. **Specificity** — Feedback identifies at least one concrete, actionable issue
   or strength in the input text.
2. **Relevance** — All feedback points are directly grounded in the provided input text;
   none are generic observations.
3. **Format** — The response is a JSON object with exactly one key, `feedback`,
   whose value is a non-empty string.
4. **No invention** — Feedback does not fabricate issues or qualities not evidenced
   in the input text.

A review response FAILS if ANY criterion above is not met.

## Response format

Respond with exactly: `PASS — <one sentence>` or `FAIL — <one sentence>`.
```

### 4.5 Runner Entry Point

```python
# tools/benchmark/runner.py
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from corpus_loader import iter_corpus
from evaluators.structural import evaluate as structural_evaluate
from evaluators.llm_judge import evaluate as judge_evaluate

STRUCTURAL_SKILLS = {"brainstorm", "spec_pipeline"}
LLM_JUDGE_SKILLS  = {"rewrite", "review"}
PASS_THRESHOLD    = 0.95
CORPUS_N          = 10


def run(skill_name: str, output_schema: dict) -> bool:
    results = []
    for entry in iter_corpus(skill_name, n=CORPUS_N):
        if skill_name in STRUCTURAL_SKILLS:
            result = structural_evaluate(entry, output_schema)
        else:
            result = judge_evaluate(entry, skill_name)
        results.append(result)
        status = "PASS" if result["pass"] else "FAIL"
        print("  [" + status + "]  job=" + result["job_id"] + "  " + result["reason"])

    total     = len(results)
    passed    = sum(1 for r in results if r["pass"])
    pass_rate = passed / total if total > 0 else 0.0
    gate      = pass_rate >= PASS_THRESHOLD and total >= CORPUS_N

    separator = "=" * 50
    print("\n" + separator)
    print("Skill:     " + skill_name)
    print("Corpus:    N=" + str(total))
    print("Pass rate: " + str(passed) + "/" + str(total) + " = " + f"{pass_rate:.0%}")
    print("Gate:      " + ("CLEARED" if gate else "NOT CLEARED") + " (need >=95%, N>=10)")
    print(separator)
    return gate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_name")
    parser.add_argument(
        "--schema-path",
        required=True,
        help="Path to skill.json containing output_schema",
    )
    args = parser.parse_args()

    schema_doc = json.loads(Path(args.schema_path).read_text())
    cleared = run(args.skill_name, schema_doc["output_schema"])
    sys.exit(0 if cleared else 1)
```

**Invocation**:

```bash
# Track A
python tools/benchmark/runner.py rewrite \
  --schema-path api/modules/ai/skills/rewrite/skill.json

python tools/benchmark/runner.py review \
  --schema-path api/modules/ai/skills/review/skill.json

# Track B
python tools/benchmark/runner.py brainstorm \
  --schema-path api/modules/ai/skills/brainstorm/skill.json

python tools/benchmark/runner.py spec_pipeline \
  --schema-path api/modules/ai/skills/spec_pipeline/skill.json
```

### 4.6 Task 2 Done — Verify

- Runner exits `0` (gate cleared) or `1` (gate not cleared) on every invocation.
- Structural evaluator: two consecutive runs on the same corpus produce identical output — deterministic by construction.
- LLM-judge evaluator: run at least 3 times on the same corpus; confirm the exit code is stable before treating a verdict as canonical.
- Both rubric documents are committed under `tools/benchmark/rubrics/`.

---

## 5. Task 3 — Track A Sync Migration

**Goal**: Migrate `rewrite` and `review` through the generic route; clear the 95%/N=10 benchmark gate; retire old routes.

**Starts after**: Task 1 merged  
**Can run in parallel with**: Task 2  
**Estimated effort**: 2 days

### 5.1 Update Skill Files

Each Track A skill needs the extended `skill.json` from Section 3.1 and a `SKILL.md` whose agent produces stdout that matches the declared `output_schema`. Add an explicit Output Contract section to each `SKILL.md`:

```markdown
## Output Contract

The agent MUST write a single JSON object to stdout and nothing else.
The exact schema is declared in `skill.json -> output_schema`.
No preamble, explanation, or trailing text may appear on stdout.
Stderr is permitted for diagnostic output only.

Valid stdout example:
  {"rewritten_text": "Improved version of the input text."}

Invalid stdout examples (all rejected by the output validator):
  Here is the rewrite: {"rewritten_text": "..."}   <- preamble not allowed
  {"rewritten_text": "...", "extra": "field"}       <- additionalProperties violation
  (empty)                                           <- not valid JSON
```

### 5.2 Wire Skills Through the Generic Route

Confirm both skills resolve correctly through `load_skill_registry`. Run a smoke test for each:

```bash
curl -s -X POST http://localhost:5000/skills/rewrite/run \
  -H "Content-Type: application/json" \
  -d '{"input": "The quick brown fox jumps over the lazy dog."}' | python3 -m json.tool
# Expected: {"rewritten_text": "..."} with HTTP 200 and X-Job-Id header

curl -s -X POST http://localhost:5000/skills/review/run \
  -H "Content-Type: application/json" \
  -d '{"input": "The quick brown fox jumps over the lazy dog."}' | python3 -m json.tool
# Expected: {"feedback": "..."} with HTTP 200 and X-Job-Id header
```

### 5.3 Run Benchmark Against Track A Corpus

```bash
python tools/benchmark/runner.py rewrite \
  --schema-path api/modules/ai/skills/rewrite/skill.json

python tools/benchmark/runner.py review \
  --schema-path api/modules/ai/skills/review/skill.json
```

**Gate condition**: Both skills print `CLEARED` with N>=10 and pass rate >=95%.

**If the gate does not clear**: Iterate on `SKILL.md` only — tune output format instructions, add valid stdout examples, reinforce the JSON-only requirement. Do not modify the runner, loosen the rubric, or remove corpus entries. Re-run after each `SKILL.md` change.

### 5.4 Retire Old Routes (post gate + production soak)

After the gate clears and real traffic confirms stability:

1. Remove handler functions from `rewrite_route.py` and `review_route.py`.
2. Remove the corresponding Blueprint registrations or `add_url_rule` calls in `app.py`.
3. Delete the now-empty old route files.
4. Remove the old per-skill paths from `openapi.yaml`.
5. Re-run the grep linter to confirm it still passes.
6. Record the retirement decision in the deployment log — not only in the commit message.

### 5.5 Track A Done — Verify

```bash
# Old routes return 404
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/rewrite -d '{"input": "test"}'
# Expected: 404

# Generic route still works
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/skills/rewrite/run \
  -H "Content-Type: application/json" -d '{"input": "test"}'
# Expected: 200

# Grep linter still clean
python ci/lint_ai_strings.py api/modules/ai/
```

---

## 6. Task 4 — Track B Async Migration

**Goal**: Migrate `brainstorm` and `spec_pipeline` through the generic route with `execution_model: async`; enforce the brainstorm output schema including `suggested_action`; clear 95%/N=10 gate; retire old routes.

**Starts after**: Track A benchmark gate cleared — Task 3 complete  
**Estimated effort**: 3 days

### 6.1 Confirm execution_model: "async" in skill.json

```json
{
  "name": "brainstorm",
  "version": "1.0.0",
  "execution_model": "async",
  "output_schema": { }
}
```

The generic route's `_handle_async` path (Section 3.4) picks this up automatically. No Python changes to the route are required for Track B.

### 6.2 suggested_action Contract

The brainstorm `SKILL.md` must instruct the agent to emit `suggested_action` in every response. Add to the Output Contract section:

```markdown
## Output Contract — brainstorm

The `suggested_action` field MUST be present in every output JSON object.
If no action can be suggested this phase, the value MUST be null — not absent.
An absent field is a schema violation and will be rejected by the output validator.

Valid:
  {
    "questions": ["..."],
    "recommendations": ["..."],
    "rewritten_braindump": "...",
    "suggested_action": null
  }

Invalid (field absent — will fail validation):
  {
    "questions": ["..."],
    "recommendations": ["..."],
    "rewritten_braindump": "..."
  }
```

### 6.3 Confirm the Polling Endpoint

The polling route is defined in Section 3.4. Verify it works end-to-end with an async skill:

```bash
# 1. Dispatch an async job
JOB_RESPONSE=$(curl -s -X POST http://localhost:5000/skills/brainstorm/run \
  -H "Content-Type: application/json" \
  -d '{"input": "I want to build a tool that helps developers write better docs"}')

JOB_ID=$(echo "$JOB_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "Job ID: $JOB_ID"

# 2. Poll until complete
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  RESULT=$(curl -s "http://localhost:5000/skills/jobs/$JOB_ID")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "[$i] status=$STATUS"
  if [ "$STATUS" = "complete" ]; then break; fi
  sleep 5
done

# 3. Inspect result — suggested_action must be present
echo "$RESULT" | python3 -m json.tool
# Expected: {"status": "complete", "result": {"questions": [...], ..., "suggested_action": null}}
```

### 6.4 Sub-Agent Blast Radius — Operational Notes

`brainstorm` and `spec_pipeline` may fan out into multiple Claude CLI subprocess calls. Current containment for this phase:

| Boundary | Mechanism |
|---|---|
| Outer timeout | Existing Claude CLI subprocess timeout (3600 s) — do not remove |
| User-facing containment | 202 + polling pattern — HTTP layer is never blocked by sub-agent depth |
| Circuit breaker | Phase 3 concern — characterise failure modes in production before designing bounds |

Document any runaway invocations observed during Track B testing in the job log. Do not add speculative circuit-breaker logic this phase.

### 6.5 Run Benchmark Against Track B Corpus

Track B uses the structural evaluator (deterministic):

```bash
python tools/benchmark/runner.py brainstorm \
  --schema-path api/modules/ai/skills/brainstorm/skill.json

python tools/benchmark/runner.py spec_pipeline \
  --schema-path api/modules/ai/skills/spec_pipeline/skill.json
```

**Gate condition**: Both skills print `CLEARED` with N>=10 and pass rate >=95%.

The structural evaluator will fail any brainstorm log where `suggested_action` is absent. Iterate on `SKILL.md` until the gate clears.

### 6.6 Retire Old Routes (post gate + production soak)

Same procedure as Section 5.4 applied to `brainstorm_route.py` and `spec_pipeline_route.py`.

### 6.7 Track B Done — Verify

```bash
# Old routes return 404
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/brainstorm -d '{}'
# Expected: 404

# Async dispatch returns 202
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/skills/brainstorm/run \
  -H "Content-Type: application/json" \
  -d '{"input": "my app idea"}'
# Expected: 202

# Poll the job and confirm suggested_action is present in result (value may be null)

# Grep linter clean
python ci/lint_ai_strings.py api/modules/ai/
```

---

## 7. Cross-Cutting Concerns

### 7.1 CI Grep Linter

```python
# ci/lint_ai_strings.py
"""
Exits 1 if any Python file under TARGET_DIR contains a string literal longer
than THRESHOLD characters. Calibrated to avoid false positives on short utility
strings. Adjust THRESHOLD with a documented comment if legitimate long strings appear.
"""
import ast
import sys
from pathlib import Path

TARGET_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("api/modules/ai")
THRESHOLD  = 80   # characters; raise with justification if needed

violations = []
for py_file in TARGET_DIR.rglob("*.py"):
    source = py_file.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if len(node.value) > THRESHOLD:
                violations.append((py_file, node.lineno, node.value[:60]))

if violations:
    print("FAIL — Long natural-language strings found in api/modules/ai/:")
    for path, lineno, preview in violations:
        print("  " + str(path) + ":" + str(lineno) + "  '" + preview + "...'")
    sys.exit(1)

print("PASS — No AI strings in Python.")
sys.exit(0)
```

**Add to CI pipeline before the test step**:

```yaml
# .github/workflows/ci.yml (or equivalent)
- name: Lint AI strings in Python
  run: python ci/lint_ai_strings.py api/modules/ai/
```

### 7.2 SKILL.md Change Triggers Benchmark Re-Run in CI

```yaml
# .github/workflows/ci.yml
- name: Detect changed skills
  id: skill-diff
  run: |
    CHANGED=$(git diff --name-only origin/main \
      | grep 'skills/.*/SKILL.md' \
      | sed 's|api/modules/ai/skills/||;s|/SKILL.md||' \
      | tr '\n' ' ')
    echo "skills=$CHANGED" >> $GITHUB_OUTPUT

- name: Run benchmark for changed skills
  if: steps.skill-diff.outputs.skills != ''
  run: |
    for skill in ${{ steps.skill-diff.outputs.skills }}; do
      python tools/benchmark/runner.py "$skill" \
        --schema-path "api/modules/ai/skills/${skill}/skill.json"
    done
```

The runner exits `1` if the gate is not cleared, blocking the PR merge. Post the runner stdout as a PR comment so the benchmark verdict is visible during review.

### 7.3 Run Log Format

Every invocation must write a log entry in this exact format. The corpus loader and benchmark runner depend on this schema being stable — treat changes as breaking.

```json
{
  "job_id":          "uuid-string",
  "skill_name":      "rewrite",
  "input":           "The user input text",
  "raw_stdout":      "{\"rewritten_text\": \"...\"}",
  "execution_model": "sync",
  "timestamp_utc":   "2026-05-07T12:00:00Z",
  "schema_valid":    true
}
```

`write_run_log(...)` is called in both `run_sync_skill` and `start_async_skill`. Sync responses carry the `job_id` in the `X-Job-Id` response header. Every invocation seeds the corpus automatically — no separate instrumentation required.

### 7.4 PR Template Additions

Add the following checklist to the repository PR template for any PR that modifies a skill file:

```markdown
## Skill Change Checklist

Required for any PR that modifies SKILL.md or skill.json:

- [ ] skill.json output_schema updated if the output shape changed
- [ ] SKILL.md Output Contract section reflects the current schema
- [ ] Benchmark runner executed locally — paste the full output below
- [ ] Max-plugin-use test: would a plain prompt with no sub-agent invocations
      produce worse output? If no, the skill does not earn its complexity.
      Justify the sub-agent invocations or simplify the skill.
- [ ] If a rubric was changed, noted explicitly as a benchmark reset
      (historical pass rates for this skill are invalidated)
- [ ] ci/lint_ai_strings.py passes locally against api/modules/ai/
```

---

## 8. Acceptance Verification Checklist

Run these checks in order. All must pass before the epic is declared complete.

### Check 1 — Zero AI strings in Python

```bash
python ci/lint_ai_strings.py api/modules/ai/
# Expected: PASS — No AI strings in Python.
```

### Check 2 — Generic route handles all four skills

```bash
# Sync skills must return 200
for skill in rewrite review; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "http://localhost:5000/skills/${skill}/run" \
    -H "Content-Type: application/json" -d '{"input": "test"}')
  echo "$skill -> $code"
done
# Expected: rewrite -> 200, review -> 200

# Async skills must return 202
for skill in brainstorm spec_pipeline; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "http://localhost:5000/skills/${skill}/run" \
    -H "Content-Type: application/json" -d '{"input": "test"}')
  echo "$skill -> $code"
done
# Expected: brainstorm -> 202, spec_pipeline -> 202
```

### Check 3 — output_schema declared for all four skills

```bash
for skill in rewrite review brainstorm spec_pipeline; do
  python3 -c "
import json
d = json.load(open('api/modules/ai/skills/${skill}/skill.json'))
assert 'output_schema' in d, 'output_schema missing'
assert 'execution_model' in d, 'execution_model missing'
print('${skill}: OK')
"
done
```

### Check 4 — Output validator rejects malformed stdout with 422

Temporarily configure a skill to emit invalid JSON, invoke the route, and confirm the response is HTTP 422 — not 200 with corrupt data in the body. Restore the skill after testing.

### Check 5 — Benchmark runner is reproducible

```bash
# Structural evaluator must produce the same exit code on consecutive runs
python tools/benchmark/runner.py brainstorm \
  --schema-path api/modules/ai/skills/brainstorm/skill.json
echo "Run 1 exit: $?"

python tools/benchmark/runner.py brainstorm \
  --schema-path api/modules/ai/skills/brainstorm/skill.json
echo "Run 2 exit: $?"
# Expected: both runs produce the same exit code
```

### Check 6 — Track A gate cleared

```bash
python tools/benchmark/runner.py rewrite \
  --schema-path api/modules/ai/skills/rewrite/skill.json
# Expected last line: Gate: CLEARED (need >=95%, N>=10)

python tools/benchmark/runner.py review \
  --schema-path api/modules/ai/skills/review/skill.json
# Expected: Gate: CLEARED
```

### Check 7 — Track B gate cleared

```bash
python tools/benchmark/runner.py brainstorm \
  --schema-path api/modules/ai/skills/brainstorm/skill.json
# Expected: Gate: CLEARED

python tools/benchmark/runner.py spec_pipeline \
  --schema-path api/modules/ai/skills/spec_pipeline/skill.json
# Expected: Gate: CLEARED
```

### Check 8 — brainstorm suggested_action present in completed job output

```bash
JOB_ID=$(curl -s -X POST http://localhost:5000/skills/brainstorm/run \
  -H "Content-Type: application/json" \
  -d '{"input": "I want to build a spec tool"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")

sleep 15

curl -s "http://localhost:5000/skills/jobs/$JOB_ID" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
result = d.get('result', {})
has_field = 'suggested_action' in result
print('suggested_action present:', has_field)
print('value:', result.get('suggested_action'))
assert has_field, 'suggested_action missing from brainstorm result'
"
# Expected: suggested_action present: True
#           value: None  (null is valid; absence is not)
```

### Check 9 — Rubric documents are checked-in artifacts

```bash
ls tools/benchmark/rubrics/
# Expected:
#   review_rubric.md
#   rewrite_rubric.md
```

**All nine checks green = epic complete.**

---

*Generated 2026-05-07 — Thin API Phase 2*

---

Here's a summary of what the guide covers and the key decisions behind its structure:

**What was generated:**

The `implementation-guide.md` is a developer-facing execution document with nine sections:

1. **Prerequisites & Orientation** — enforces the dependency DAG (T1 → T2+T3 in parallel → T4), names the "zero AI strings" invariant as a pre-PR gate, and frames the rollback surface explicitly
2. **Repository layout** — the full file tree after Phase 2, including which old routes survive until each retirement gate clears
3. **Task 1 (Registry Contract)** — canonical `skill.json` schemas for all four skills (including `suggested_action` in brainstorm), the OpenAPI-first endpoint declaration, `output_validator.py` with its exact `OutputValidationError` contract, the generic route using a handler registry dict instead of if/else, and the service split at the 200-line boundary
4. **Task 2 (Benchmark Runner)** — corpus loader, structural evaluator (deterministic JSON Schema check for async skills), LLM-as-judge evaluator (routed through the chain adapter per P1), both rubric documents as versioned markdown artifacts, and the runner entry point with correct exit code semantics
5. **Task 3 (Track A)** — Output Contract section template for `SKILL.md`, smoke tests, the iterate-on-SKILL.md-only failure mode, and the four-step retirement sequence
6. **Task 4 (Track B)** — the `suggested_action` null-but-present contract, full async smoke test with polling loop, sub-agent blast radius table, and the structural evaluator as the gate mechanism
7. **Cross-Cutting Concerns** — the grep linter (AST-based, threshold-calibrated), the CI SKILL.md-change trigger, the stable run log format, and the PR template checklist including the max-plugin-use test
8. **Acceptance Verification** — nine runnable shell checks, one per epic success criterion, with expected output annotated inline