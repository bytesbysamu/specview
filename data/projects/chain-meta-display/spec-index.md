---
sidebar_position: 0
---

# Chain Meta Display -- Lint + Score Panels

> Render sidecar metadata (lint warnings, quality scores) from chain runs in collapsible UI panels below the tabbed output on the /text page. The backend already returns `meta: { lint, score }`. The frontend ignores it. This spec set adds collapsible panels that parse the JSON and render structured scores.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Problem, constraints, resolved decisions |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Component design, data flow, styling |
| [Timeline](./timeline.md) | Status tracking |

## Overview

The chain runner fix (see [Chain Runner Fix spec set](../chain-runner-fix-1776426025036/spec-index.md)) plumbs `meta: { lint: "...", score: "..." }` from sidecar steps through the DTO layer to the API response. That spec set explicitly deferred UI rendering as out of scope. This spec set picks it up.

The `braindump-to-docs` chain returns lint readiness flags (from the pre-flight lint step) and quality dimension scores (from the post-generation review step) as raw JSON strings inside `meta`. Today the frontend `ChainResponse` interface lacks the `meta` field and the /text page discards it. After this work:

1. `ChainResponse` interface and mock gain the `meta` field
2. `text.page.ts` stores `meta` from the chain response
3. A new `ChainMetaPanelsComponent` renders lint and score data in collapsible panels below the chain output tabs
4. Panels are collapsed by default with an "Inspector" toggle header
5. Lint renders as pass/fail badges per dimension; scores render as labeled bars

## Key Decisions

- **Collapsed by default** -- clean UI; "Inspector" toggle keeps it discoverable without cluttering the primary output
- **Structured rendering, not raw JSON** -- parse the JSON and display score bars + pass/fail badges; raw JSON fallback if parsing fails
- **Single component** -- `ChainMetaPanelsComponent` handles both lint and score sections; no separate components per meta key
- **No backend changes** -- this is purely frontend; `meta` plumbing ships with the chain runner fix epic
- **Graceful degradation** -- if `meta` is absent or malformed, panels simply don't render; no error states

## Dependency

This spec set depends on the chain runner fix shipping first: [Chain Runner Fix epic](../chain-runner-fix-1776426025036/epic.md). Without the `meta` field on `ChainRunResult` and the DTO/service plumbing, there is no data to display. The mock path (`environment.useMocks.textChains`) can be used for development before the backend ships.

## Related Documents

- [Analysis](./analysis.md) -- problem and constraints
- [Epic](./epic.md) -- scope and tasks
- [Architecture](./architecture.md) -- component design
- [Timeline](./timeline.md) -- status tracking
- [Chain Runner Fix spec set](../chain-runner-fix-1776426025036/spec-index.md) -- prerequisite (plumbs `meta` to API response)

===END===
