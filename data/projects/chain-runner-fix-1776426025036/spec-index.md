---
sidebar_position: 0
---

# Chain Runner Fix -- OutputKey Sidecar

> Fix the chain runner's step-forwarding logic so that steps with `outputKey` sidecar their result as metadata instead of replacing the pipeline input, and surface sidecar data to the frontend via a new `meta` field on `ChainRunResult`.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Root cause, constraints, resolved decisions |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design for the fix |
| [Timeline](./timeline.md) | Status tracking |

## Overview

The chain runner (`definition_runner.py`) has a step-forwarding bug: line 246 unconditionally sets `current_text = result.text` after every step, regardless of whether the step has an `outputKey`. This means steps intended as sidecar operations (lint pre-flight, quality scoring) replace the pipeline input instead of preserving it.

The `braindump-to-docs` chain exposes all four symptoms:

1. **Step 1 (lint, `outputKey: "lint"`)** runs correctly but its JSON output becomes Step 2's input -- Step 2 receives lint JSON instead of the user's braindump.
2. **Step 2 (generate)** produces specs from lint JSON instead of the original braindump, degrading output quality or producing nonsense.
3. **Step 3 (review, `outputKey: "score"`)** produces quality-score JSON that becomes the final output -- the user sees `{"scores": {...}, "issues": [...]}` instead of their generated spec files.
4. **`ChainRunResult`** has no `meta` field, so even if sidecar results were correctly separated, there is no way to carry them to the frontend.

The fix is surgical: four changes across two files (runner + DTO), no new modules, no schema changes. The `rewrite-review` and `deep-humanize` chains are unaffected because they don't use `outputKey`.

## Key Decisions

- **Sidecar, not discard** -- `outputKey` steps store their result in a `meta` dict and do NOT mutate `current_text`
- **Original input always accessible** -- steps with `outputKey` receive `current_text` (which is `user_input` if no prior non-sidecar step has run), preserving the pipeline's main data flow
- **`meta` exposed to frontend** -- `ChainRunResult`, `ChainResponse` DTO, and frontend `ChainResponse` interface all gain an optional `meta: dict[str, str]` field so the UI can display lint warnings and quality scores in collapsible panels
- **Backward-compatible** -- chains without `outputKey` steps behave identically; `meta` is `None`/omitted when empty

## Related Documents

- [Analysis](./analysis.md) -- root cause walkthrough
- [Epic](./epic.md) -- scope and tasks
- [Architecture](./architecture.md) -- technical design
- [Timeline](./timeline.md) -- status tracking
- [Text Chains Epic](../text-chains-1776379250140/epic.md) -- parent epic that shipped the chain runner

===END===
