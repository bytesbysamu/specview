---
sidebar_position: 1
---

# Analysis -- Chain Meta Display

**Purpose**: Surface the problem, constraints, and resolved decisions before scoping the frontend work.

**Date**: 2026-04-17

---

## Problem

The `braindump-to-docs` chain runs three steps: lint (pre-flight readiness check), generate (spec file creation), and score (post-generation quality review). The lint and score steps produce structured JSON that flows through the backend as `meta: { lint: "...", score: "..." }` on the API response. The frontend discards this data. The user has no visibility into what the lint caught or how their generated specs scored. Without this feedback loop, the pipeline improves silently and the user never learns why one braindump produces better specs than another.

## Hard Constraints

- **Feature = Bounded Context** -- the new component lives inside `pages/text/components/`. No cross-feature imports. It receives data via `@Input`, not via a shared service.
- **Standalone Components, OnPush, Signals** -- no NgModules. The component is standalone with OnPush change detection. Internal toggle state via Angular signals.
- **data-test selectors only** -- every interactive element gets a `data-test` attribute. Tests never query by class, id, or tag.
- **No backend changes** -- this epic is frontend-only. The `meta` field plumbing ships with the chain runner fix. If that hasn't shipped yet, mock data covers the development path.
- **Adapter boundary** -- `TextApiService` is the only surface that touches the backend. The component receives parsed data from the page, not raw HTTP responses.
- **Dark-only, no toggle** -- Bubls is dark-only. Panels use existing CSS tokens (`--surface`, `--hairline`, `--text-muted`, `--accent-sage`). No light-mode considerations.

## Open Questions (resolved)

| Question | Resolution | Rationale |
|---|---|---|
| Structured rendering or raw JSON dump? | Structured with raw JSON fallback. | Structured (score bars, pass/fail badges) is better UX. Raw JSON is the fallback when parsing fails. The braindump explicitly asked for structured. Effort is bounded because the JSON shapes are known and stable (lint has `issues[]`, score has `scores{}`). |
| Show panels by default or collapsed? | Collapsed with "Inspector" toggle. | The braindump flagged this tension. Collapsed keeps the primary output clean. The "Inspector" label signals the panels are diagnostic/meta, not primary content. A `data-test="meta-toggle"` button toggles visibility. |
| Does `rewrite-review` meta render differently from `braindump-to-docs` meta? | No -- same component, same layout. | The `rewrite-review` chain's meta (when it eventually gets `outputKey` steps) would have the same JSON shape (issues + scores). One component handles both. The braindump raised this as a question; the answer is that the JSON contract is the same regardless of chain origin. |
| Where does the component sit in the DOM? | Below `<app-chain-output-tabs>`, inside the same `.result` section. | The panels are metadata about the chain output, so they belong in the result section. Placing them below the tabs preserves the reading order: output first, diagnostics second. |
| Who parses the JSON strings? | The page component (`text.page.ts`) parses `meta` values from strings to typed objects and passes them as `@Input` to the panel component. | Keeps the panel component pure (receives typed data, renders it). Parsing failure is handled in the page: if JSON.parse throws, the panel gets `null` and doesn't render. |

## Dependencies

| Dependency | Status | Location |
|---|---|---|
| Chain runner fix (meta plumbing) | Spec'd, not shipped | [Chain Runner Fix epic](../chain-runner-fix-1776426025036/epic.md) |
| `ChainResponse` interface (frontend) | Missing `meta` field | `src/app/services/text-api.service.ts` line 14 |
| `ChainResponse` mock | Missing `meta` data | `src/app/mocks/chain.mock.ts` |
| `ChainOutputTabsComponent` | Shipped | `src/app/pages/text/components/chain-output-tabs.component.ts` |
| `TextPage` component | Shipped | `src/app/pages/text/text.page.ts` |
| CSS design tokens | Shipped | `--surface`, `--hairline`, `--text-muted`, `--accent-sage`, `--r-sm`, `--sp-*` |

## Explicitly Out of Scope

- Backend changes to `ChainRunResult`, `ChainResponse` DTO, or `chain_service.py` -- that is the chain runner fix epic
- Persisting meta data to the database -- meta is ephemeral display data
- Analytics events for meta panel interactions -- no consumer exists yet
- Editing or re-running chains based on lint/score feedback -- future capability
- Score trend tracking across multiple braindump runs -- requires persistence, deferred

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
