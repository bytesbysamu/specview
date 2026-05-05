# spec-doc — Pipeline Self-Improvement (linter + coherence + structured prior contracts)

## What

Close the leaky feedback loop between hand-fixed specs and the next generation. Today every production-quality bug — leaked thinking lines, stale model attribution, file-path drift across sibling tasks, mismatched test counts — is caught at one of three places: the executor's eye on first read, the executor's grep after a regen, or the user's hand-fix commit (e.g. `729e5c1` "minimal-fix pass on spec docs"). None of these write back into the prompt. A pre-emit linter writes the bug class as code; the bug class then cannot ship.

This brain dump bundles four things that share one surface (`api/modules/quality/`):

1. **Pre-emit linter** that runs before every `update_file()` write.
2. **Multi-doc coherence pass** that runs after each task generation.
3. **Structured prior-task contracts** that replace the 60-line truncation in `task_gen/service.py:163`.
4. **`versions.md` injection** that fixes the stale `Sonnet 4.6` co-author leak.

Plus one tiny endpoint: `POST /api/projects/<id>/repair` to retroactively generate `spec-index.md` and `timeline.md` for older projects missing them.

### 1. Pre-emit linter — `api/modules/quality/lint.py`

Pure function `lint_task_guide(text: str) -> list[Flag]`. Wired into `task_gen/service.py:run_generation` immediately before `update_file()`. On any error-severity flag, return 502 from the polling endpoint with the flag list — Angular shows a toast; user clicks Regenerate. On warning-severity, write the file but include a `warnings: [...]` field in the polling response.

```python
# modules/quality/lint.py
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Flag:
    rule: str
    severity: str  # "error" | "warning"
    message: str
    line: int | None = None


_PREAMBLE = re.compile(r"^(Now I have|Let me write|Writing the guide|Here's the guide|Below is the guide)", re.M)
_ABSPATH  = re.compile(r"/Users/[a-z]+|/home/[a-z]+|C:\\Users\\")
_PLACEHOLDER = re.compile(r"path/to/[a-z]+|<placeholder>|TODO\(executor\)|<TBD>")
_EMPTY_TEST  = re.compile(r"/\*\s*\.\.\.\s*\*/|it\([^,]+,\s*\(\)\s*=>\s*\{\s*\}\)")
_ABS_COUNT   = re.compile(r"Expected[:\s].*?\b(\d{2,3}) passed\b")

def lint_task_guide(text: str) -> list[Flag]:
    flags = []
    # 1. Must start with #
    if not text.lstrip().startswith("#"):
        flags.append(Flag("starts_with_hash", "error", "Doc does not start with #"))
    # 2. No preamble strings
    for m in _PREAMBLE.finditer(text):
        flags.append(Flag("preamble", "error", f"Leaked thinking: {m.group()[:60]!r}", text[:m.start()].count("\n") + 1))
    # 3. Stale model attribution
    if "Co-Authored-By: Claude" in text and "Claude Opus 4.7" not in text:
        flags.append(Flag("stale_attribution", "warning", "Co-Author line should match EXECUTOR_ATTRIBUTION (Opus 4.7)"))
    # 4. Absolute test counts in Expected blocks
    for m in _ABS_COUNT.finditer(text):
        flags.append(Flag("absolute_count", "warning", f"Use N → N+K instead of '{m.group(1)} passed'"))
    # 5. Personal paths
    for m in _ABSPATH.finditer(text):
        flags.append(Flag("personal_path", "error", f"Personal path: {m.group()}"))
    # 6. Placeholder paths/values
    for m in _PLACEHOLDER.finditer(text):
        flags.append(Flag("placeholder", "error", f"Placeholder left in: {m.group()}"))
    # 7. Empty test bodies
    if _EMPTY_TEST.search(text):
        flags.append(Flag("empty_test", "error", "Test body is empty (`/* ... */` or `() => {}`)"))
    # 8. Section count — must have all 10 numbered sections
    section_headers = re.findall(r"^## \d+\. ", text, re.M)
    if len(section_headers) != 10:
        flags.append(Flag("missing_section", "error", f"Expected 10 numbered sections, found {len(section_headers)}"))
    # 9. +K tests claim consistency
    test_claims = re.findall(r"\+(\d+) (?:new )?tests?", text)
    if test_claims and len(set(test_claims)) > 1:
        flags.append(Flag("count_mismatch", "error", f"+K test claim is inconsistent: {test_claims}"))
    return flags
```

~120 lines including tests. Each rule is one regex and a one-line action.

### 2. Multi-doc coherence pass — `api/modules/quality/coherence.py`

`lint_capability(project_dir: Path) -> list[Flag]` runs after task generation completes. Eight invariants:

| # | Invariant |
|---|---|
| 1 | Symbol uniqueness across `## 3. Files` tables across all task docs (no path is `(new)` in two tasks) |
| 2 | Cross-task file-path consistency (if `from X import Y` and `from X.sub import Y` both appear in different tasks, flag) |
| 3 | Epic task-table rows match `task-{num}-*.md` filenames on disk |
| 4 | `spec-index.md` Task Guides table matches filesystem reality |
| 5 | `timeline.md` Backlog matches `epic.md` task table by num + name |
| 6 | Every component named in `architecture.md` Component Design has a task that produces it |
| 7 | If task N's Pre-flight cites a symbol from task M (M < N), task M's Files table must declare creating it |
| 8 | CONTENT ROUTING: status terms only in `timeline.md` |

Exposed as `POST /api/projects/<id>/coherence` returning `{flags, summary}`. Angular surfaces unresolved flags as a project-card badge.

### 3. Structured prior contracts — fix `task_gen/service.py:163`

Today, `collect_prior_task_content` truncates each prior task to **60 lines**. That cuts off §3 (Files) and §5 (Tests). The next task's prompt cannot see what prior tasks declared as `(new)` files — which is the structural cause of the contract drift in §1.3 of the report.

Replace the truncation with a parser:

```python
# modules/task_gen/service.py
def collect_prior_task_contracts(project_dir: Path, current_task_num: str) -> dict:
    """Return {task_num: {creates: [...], modifies: [...], exports: [...]}}."""
    contracts = {}
    for path in sorted(project_dir.glob("task-*.md")):
        m = re.match(r"task-([\d.]+)-", path.name)
        if not m or _ge(m.group(1), current_task_num):
            continue
        text = path.read_text()
        contracts[m.group(1)] = _parse_task_contract(text)
    return contracts
```

The parser pulls `### To Create (new)` and `### To Modify` rows from §3, plus any `**Exports**` block from §3a (see §6.3 of the report). Pass the dict to the impl-guide prompt as a new `## PRIOR-TASK CONTRACTS (do not re-create these files)` block.

This is a **one-bug fix** that produces compounding value — every multi-task generation from now on sees the right contract set.

### 4. `versions.md` injection — kill the stale Sonnet 4.6 leak

New context block injected by `bootstrap_project` and `task_gen.service.run_generation`:

```python
# Read once at startup
EXECUTOR_VERSIONS = {
    "executor_model": os.environ.get("CLAUDE_CODE_MODEL", "claude-opus-4-7"),
    "co_author_line": "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>",
}
```

Inject as a `## EXECUTOR ATTRIBUTION` block in the impl-guide prompt template. Add a Hard Rule to `_USER_HEADER` in `api/modules/implementation_guide/prompts.py`:

> **When emitting a `Co-Authored-By:` trailer, copy the value from EXECUTOR ATTRIBUTION verbatim. Never invent a model version or attribution.**

Lint rule #3 above is the safety net.

### 5. Project repair endpoint — `POST /api/projects/<id>/repair`

Re-runs the deterministic template generators (`generate_spec_index`, `generate_timeline`, `generate_readme`) for any project missing those files. ~30 lines. Catches the architecture-cleanup-style projects from §1.6 of the report.

```python
@projects_bp.post("/<id>/repair")
def repair(id: str):
    proj = get_project(id)
    if not proj:
        return jsonify({"error": "not found"}), 404
    repaired = []
    for filename, generator in [
        ("spec-index.md", generate_spec_index),
        ("timeline.md", generate_timeline),
        ("README.md", generate_readme),
    ]:
        if not (proj.dir / filename).exists():
            (proj.dir / filename).write_text(generator(proj))
            repaired.append(filename)
    return jsonify({"repaired": repaired})
```

## Why now

The Workflows-as-a-Domain-Layer epic just landed (commits `5bc8722` + `6083160`). That epic's hand-fix pass (commit `729e5c1`) is the highest-cost evidence of the leaky loop the report describes — four sibling task docs disagreed on `events.py` location and field names; the user spent a session reconciling. The linter + coherence pass would have flagged that drift at generation time and forced a real prompt-side fix.

The encoded pattern that already works (`_BOOTSTRAP_CONTENT_ROUTING` in `prompts/__init__.py:129-139`) is *negative rules with a routing matrix* — the cheapest, highest-leverage encoding in the pipeline today. The linter generalises that pattern from "rules the model is asked to follow" to "rules the artefact is checked against." One is a wish; the other is a contract.

The 60-line truncation root cause is the most surprising finding from the report. It's a single-file, single-line fix that compounds across every future multi-task generation.

## What's missing

Two decisions:

1. **Where do the linter flags surface in the UI?** Options:
   - (a) Toast in the Angular sidebar after Regenerate (proposed) — minimal Angular change
   - (b) Inline panel in the project view showing all current flags
   - (c) Polling response carries `warnings: [...]` and the existing snapshot UI renders them

   Pick (a) for now; (c) is the natural follow-up once flags accumulate enough to warrant a permanent surface.

2. **Does the linter block generation or warn?** Errors block (502 from the polling endpoint). Warnings write the file with a `warnings` field. The classification is per-rule above and should not be made configurable until a real "I want to ship the warning" case appears.

## Explicitly out of scope

- **Auto-retry with prompt amendment** — when the linter rejects, the user clicks Regenerate, period. No "self-healing" loop until the linter's error rate stabilises.
- **Persistent flag history** — the linter's job is to gate, not to dashboard. Flag-pattern analytics across runs is a phase-2 retro endpoint.
- **Auto-fixers for warning-severity flags** — the linter detects; humans decide. Auto-fix for trivial cases (preamble strip, attribution rewrite) can land as a separate brain dump once we see the failure-rate distribution.
- **Coherence pass running during task generation** — runs only post-task. Mid-generation coherence checking would require holding partial state across tasks, which the in-process model can't easily support.
- **Replacing the impl-guide prompt template wholesale** — the prompt edits in §6 of the report are bundled with the structured-prior-contracts work above; no other prompt rewrite is in scope.
