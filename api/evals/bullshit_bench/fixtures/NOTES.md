# BullshitBench v2 — Fixture Notes

## Dataset

- Source: https://github.com/petergpt/bullshit-benchmark (`questions.v2.json`, main branch)
- Vendored: 2026-05-21
- Format: the upstream file is a metadata envelope (`benchmark`, `version`, `scoring`, `counts`, `techniques`).
  Questions are nested under `techniques[*].questions[]` — 13 technique blocks, 100 questions total.
- Each record has the fields: `id`, `question`, `nonsensical_element`, `domain`, `domain_group`, `technique`,
  `difficulty`, `difficulty_label`, `is_control`.

Required eval fields and their upstream names:

| Eval field            | Upstream field        |
|-----------------------|-----------------------|
| question text         | `question`            |
| known nonsensical element | `nonsensical_element` |
| domain classification | `domain_group`        |
| nonsense technique    | `technique`           |

Domain groups: `software` (40), `finance` (15), `legal` (15), `medical` (15), `physics` (15).

## Model Identity (adapter.rewrite path)

When `CHAIN_PROVIDER=cli` is set, `adapter.rewrite()` calls `providers/cli.py::create_message()`.
That function builds a subprocess command:

```
claude -p --output-format text --system-prompt <system> --model <model>
```

The `model` parameter is passed directly via `--model`. The eval runner should pass `model="claude-opus-4-6"`
(the adapter `DEFAULT_MODEL`) unless overriding at call time. No agent routing (`--agent chain-agent`)
occurs because `rewrite()` always provides a system prompt, which bypasses the `_CHAIN_AGENT` code path
in `_build_cmd()`.

Token counts are always `None` from the CLI provider — `create_message` returns `(text, None, None)`.
Latency is measured wall-clock by `adapter.rewrite()` via `time.monotonic()`.

## Anonymous Analysis Prompt — Context Injection Audit

The public analysis path (`modules/ai/services/public_analyze.py::run_analysis`) calls:

```python
adapter.rewrite(system=_ANALYSIS_SYSTEM, prompt=prompt, model="claude-haiku-4-5", max_tokens=2048)
```

`adapter.rewrite()` does NOT call `with_context()`. Context injection (`## BUILDER CONTEXT` and
`## PRINCIPLES` sections) only happens inside `adapter.generate()` and `adapter.stream()`, not
`adapter.rewrite()`.

Conclusion: **no builder context and no engineering principles are injected** into the anonymous
analysis prompt. The system prompt is the literal string `"You are a markdown spec writer."` — nothing
more. The "no speculative abstractions" phrasing observed in a manual test was not caused by
builder context leaking in; it arose from the content of `_ANALYSIS_USER` template itself, which
instructs the model to keep output short and structured, naturally suppressing speculative content.

The eval runner should also use `adapter.rewrite()` to match the production path and ensure no
context bleed.
