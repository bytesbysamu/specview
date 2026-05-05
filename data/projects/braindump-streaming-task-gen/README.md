# spec-doc-api — Streaming Task Generation via SSE

> **MERGED** into `braindump-saas-reliability.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P3 — UX win, not reliability blocker.
> **Effort**: ~1 day (CLI streaming mode + partial buffer); +0.5 day for SSE endpoint.
> **Blocks**: nothing — additive over the existing polling pattern.
> **Depends on**: nothing structural; benefits when the SDK provider is the default
>                (CLI's `--output-format stream-json` works but SDK is cleaner).
> **Siblings**: `braindump-bootstrap-async.md` (same polling pattern; bootstrap inherits the partial field for free),
>               `braindump-saas-anthropic-sdk-provider.md` (preferred streaming path),
>               `braindump-retry-recovery.md` (consumes early failure detection from the partial buffer).

## What

Add a Server-Sent Events (SSE) stream endpoint alongside the existing polling GET so Angular can show real-time progress during task generation: character-by-character output from Claude, current step label, estimated completion. The polling endpoint stays — SSE is additive, not a replacement.

The current experience: click "Generate", spinner spins for 8–15 minutes, file appears. No feedback. Users assume it's stuck. SSE gives the same UX as Claude.ai's streaming chat response.

### 1. CLI provider — add streaming mode

The Claude CLI already supports streaming output via `--output-format stream-json`. Switch from `subprocess.run` (blocking) to `subprocess.Popen` with line-by-line stdout reads:

```python
# modules/chain/providers/cli.py
def stream_message(system: str, prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 16384):
    cmd = [
        "claude", "-p",
        "--output-format", "stream-json",
        "--max-tokens", str(max_tokens),
    ]
    if system:
        cmd.extend(["--system-prompt", system])

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.stdin.write(prompt)
    proc.stdin.close()

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {}).get("text", "")
            if delta:
                yield delta
        elif event.get("type") == "message_stop":
            break

    proc.wait()
    if proc.returncode != 0:
        raise ProviderError(f"claude CLI exited {proc.returncode}: {proc.stderr.read()[:200]}", 502)
```

### 2. Chain adapter — stream_generate()

```python
# modules/chain/adapter.py
def stream_generate(system: str, user: str, *, max_tokens: int = 16384):
    """Yields text deltas from the provider."""
    yield from _provider().stream_message(system, user, max_tokens=max_tokens)
```

The existing `generate()` keeps blocking behavior. Both coexist.

### 3. Background thread — accumulate streaming output

```python
# modules/task_gen/service.py  (in run_generation, step 9)
chunks = []
for delta in chain_adapter.stream_generate(system, user):
    chunks.append(delta)
    # Update progress buffer in STATE (non-blocking read)
    with _LOCK:
        STATE[slot_key]["partial"] = "".join(chunks[-500:])  # last 500 chars for display
result_text = "".join(chunks)
```

`partial` is a rolling window of the last 500 characters. Angular displays this in a pre-formatted box while polling.

### 4. GET status endpoint — return partial field

```python
# Existing snapshot() — add partial to output
for key in ("allDone", "filename", "taskNum", "taskName", "error", "partial"):
    value = entry.get(key)
    if value is None:
        continue
    out[key] = value
```

Angular already polls every 3s. With `partial` in the response, the existing polling loop gets live preview for free — no SSE client needed.

### 5. Angular — live preview in polling loop (minimal change)

```typescript
// new-project.component.ts or generate-task modal
while (true) {
  await new Promise(r => setTimeout(r, 3000));
  const status = await firstValueFrom(this.taskGenService.getStatus(projectId));
  if (status.partial) {
    this.livePreview = status.partial;  // bind to <pre> in template
  }
  if (status.done) { break; }
}
```

No SSE client, no EventSource API. The rolling partial preview via polling is good enough for the feedback goal.

### 6. True SSE endpoint (optional, phase 2)

```python
# modules/task_gen/routes.py
@task_gen_bp.get("/<project_id>/generate-task/stream")
def stream_generate_task(project_id: str):
    def event_stream():
        last_len = 0
        while True:
            entry = service.snapshot(project_id)
            partial = entry.get("partial", "")
            if len(partial) > last_len:
                new_text = partial[last_len:]
                yield f"data: {json.dumps({'delta': new_text})}\n\n"
                last_len = len(partial)
            if entry.get("done"):
                yield f"data: {json.dumps({'done': True})}\n\n"
                return
            time.sleep(0.5)
    return Response(event_stream(), mimetype="text/event-stream")
```

Consumer: Angular `EventSource`. Delivers sub-second updates instead of 3s polling.

## Why now

The generate-task flow takes 8–15 minutes. A progress preview changes the perceived experience from "broken?" to "working, here's what Claude is writing." The `partial` field in polling is a zero-SSE-client change — it uses the infrastructure already built.

## What's missing

One decision: **partial buffer strategy**. Rolling last-500-chars is simple but the user sees the tail, not a progress indicator. Options:
- (a) Rolling tail (proposed) — simplest, shows Claude's most recent output
- (b) Full accumulation — `partial` grows to full output size (memory concern for 16k tokens)
- (c) Character count only — `{"bytesWritten": 4200, "estimatedTotal": 16000}` — progress bar without content

Option (a) for display, option (c) for a progress bar. Both fit in the same polling response.

## Explicitly out of scope

- WebSocket (bidirectional) — SSE is one-way server push, which is all that's needed
- Streaming for bootstrap chain — bootstrap is fire-and-forget (async 202), progress there is less critical
- Per-step progress events ("now running step 3 of 11") — requires instrumenting run_generation with named phases
