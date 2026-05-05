# spec-doc-api — Raise max_tokens for Long-Form Generations

> **Priority**: P0 (acute) — silently truncating output today.
> **Effort**: ~30 min for the CLI fix, +1h for truncation heuristic.
> **Blocks**: bootstrap-async (per-step `max_tokens` is meaningless if CLI drops it),
>            saas-anthropic-sdk-provider (SDK respects it correctly — SDK migration
>            sidesteps the bug, but until SDK is the default, CLI users still hit it).
> **Depends on**: nothing.
> **Siblings**: `braindump-saas-anthropic-sdk-provider.md` (SDK is the durable fix),
>               `braindump-bootstrap-async.md` (consumer of per-step `max_tokens`).

## What

Three things, all small, all in the chain provider layer:

1. **Fix the CLI provider's silent drop of `max_tokens`.** `chain.adapter.generate(...)` already accepts `max_tokens`, the CLI provider already accepts it as a parameter — but the CLI provider's `subprocess.run` invocation **does not pass it to the `claude` CLI**. So today, `chain_adapter.generate(system, user, max_tokens=16384)` silently ceilings at the CLI's default. This is the load-bearing bug.
2. **Pass `max_tokens=16384` from call sites that produce long output.** Architecture step in bootstrap, implementation guides in task_gen.
3. **Add a 5-line truncation heuristic** in `task_gen/service.py` that flags the file as `warnings: ["may be truncated"]` rather than silently shipping a half-document.

The visible failure today: Task 1 of the Workflows project was cut at 65 lines, mid-`# Task` header, no error, no warning. The user saw a doc that began with mid-content because the model ran out of tokens and the executor wrote whatever it had.

### 1. Fix CLI provider — actually pass `--max-tokens`

`api/modules/chain/providers/cli.py` currently:

```python
def create_message(system, prompt, *, model="claude-sonnet-4-5", max_tokens=4096) -> str:
    cmd = ["claude", "-p", "--output-format", "text"]
    if system:
        cmd.extend(["--system-prompt", system])
    # max_tokens is accepted but never forwarded to the subprocess
    ...
```

Fix:

```python
def create_message(system, prompt, *, model="claude-sonnet-4-5", max_tokens=4096) -> str:
    cmd = ["claude", "-p", "--output-format", "text", "--max-tokens", str(max_tokens)]
    if system:
        cmd.extend(["--system-prompt", system])
    ...
```

Two-line diff (one new flag, one new arg). Verify the CLI version installed accepts `--max-tokens`; if not, the deployed CLI needs updating. **This must land before any caller starts passing larger values, or the change is a no-op.**

### 2. Update call sites that need 16k

```python
# modules/task_gen/service.py — implementation guides run long
result = chain_adapter.generate(system, user, max_tokens=16384)
```

```python
# modules/spec_gen/workflows/generate_spec.py — architecture step in particular
.step(AICall(
    name="architecture",
    system=ARCHITECTURE_SYSTEM,
    prompt_template=ARCHITECTURE_USER,
    input_keys=("braindump", "project_name", "builder", "principles", "epic", "codebase", "references"),
    max_tokens=16384,   # was 4096
))
```

`AICall` already takes `max_tokens` per Task 1.2. The bootstrap workflow (see `braindump-bootstrap-async.md`) sets `max_tokens` per step; this brain dump just confirms 16k is the right value for the long-form steps.

### 3. Truncation heuristic — `task_gen/service.py`

```python
def _looks_truncated(text: str) -> bool:
    """Heuristic: response ends mid-block, mid-sentence, or below a sane minimum."""
    if len(text) < 500:
        return True
    last = text.rstrip()[-200:]
    # Unbalanced ``` fences
    if text.count("```") % 2 == 1:
        return True
    # Ends mid-sentence (no terminal punctuation in the last line)
    last_line = text.rstrip().split("\n")[-1].strip()
    if last_line and last_line[-1] not in ".?!:`)]}>":
        return True
    return False
```

In `run_generation`, after the chain call:

```python
warnings = []
if _looks_truncated(result.text):
    warnings.append("output may be truncated — ran into max_tokens ceiling")

# Write the file regardless — partial output is better than nothing
update_file(project_dir, project_id, filename, result.text)

with _LOCK:
    STATE[slot_key].update({"done": True, "warnings": warnings, ...})
```

Angular reads `warnings` from the polling response and shows a yellow badge on the affected task card. User clicks Regenerate; same prompt runs again with the larger ceiling already in place.

## Why now

Truncation is the single most common quality failure in the tool today. It is silent — there is no error, no warning, no badge. The CLI provider's `--max-tokens` drop is a one-line fix that has been latent since the provider was written; nobody noticed because the default 4096 was the default everywhere.

The fix unlocks two downstream things:

- **The structured prior contracts in the linter brain dump** require seeing the full §3 + §5 of prior tasks. With 4096-token truncation, even short epics produce truncated impl guides, which in turn truncate the prior-context blob the next task sees. Raising the ceiling is a precondition for the contract-passing fix to compound.
- **The bootstrap async migration** sets per-step `max_tokens` in `BOOTSTRAP_WORKFLOW`. If the CLI provider drops the flag, the per-step tuning is meaningless — every step gets the CLI default regardless of what the workflow declares.

## What's missing

One decision: **what to do when truncation is detected**.
- (a) Write the file + warning badge (proposed) — user inspects, decides whether to regenerate. Lowest friction.
- (b) Auto-retry with prompt amendment ("continue from where you left off") — risky; Claude often restarts.
- (c) Refuse to write; surface error — safest but forces a manual loop on every truncation.

(a) is right for now. (b) is a future "auto-recovery" brain dump; (c) defeats the point of having a heuristic warning.

## Explicitly out of scope

- **Streaming output to avoid the ceiling entirely** — `braindump-streaming-task-gen.md` covers this. Streaming lets the executor consume chunks as they arrive, which sidesteps the per-call `max_tokens` ceiling for some workflows. Out of scope here; this brain dump is the synchronous-call fix that ships in days, not weeks.
- **Per-call `max_tokens` in the API request body** — callers don't need to tune this; it's a per-step compile-time constant in the workflow definition.
- **Token-cost accounting tied to `max_tokens`** — `braindump-multi-provider-cost-visibility.md` covers usage tracking.
- **Anthropic SDK provider** — same brain dump. The SDK provider's `max_tokens` already works; this brain dump is the CLI-side parity fix.
- **`max_tokens` for the analysis and epic prompts** — they fit comfortably in 4096 today and the default stays. Only the architecture step + impl-guide step are getting raised.
