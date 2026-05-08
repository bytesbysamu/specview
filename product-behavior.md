# Product Behavior Contract

> Mirrored 1:1 by `e2e/features/`. Any flow change here must be reflected there.

## Flow 1 — Brainstorm

**Trigger**: User submits text to the brainstorm action.
**Steps**: POST /api/brainstorm → 200 + {text, latencyMs} → result rendered inline.
**Duration class**: Short (< 60s synchronous).
**Failure shape**: 500 + {"error": "..."} → error message shown in UI.

## Flow 2 — Brainstorm → Pipeline

**Trigger**: User starts spec pipeline from brainstorm output.
**Steps**: POST /api/bootstrap → {job_id} → poll /api/bootstrap/{job_id} → done:true → files listed in sidebar.
**Duration class**: Long (60–180s async).
**Failure shape**: Poll returns error field → [data-test="polling-error"] visible.

## Flow 3 — Epic-Guide Generation

**Trigger**: User clicks "Generate Guide" on a project.
**Steps**: POST /api/projects/{id}/generate-epic-guide → {job_id} → poll status → done:true → guide file appears.
**Duration class**: Medium (30–90s async).
**Failure shape**: Same as Flow 2.

## Flow 4 — Billing Gate (Free Tier)

**Trigger**: Free-tier user calls an AI action above their daily limit.
**Steps**: Backend checks usage → 429 + {error, limit, reset_at, upgrade_url} → upgrade prompt shown; no skill invoked.
**Duration class**: Immediate (< 1s).
**Failure shape**: 429 response; no job enqueued; no polling.

## Flow 5 — Pro Subscription Check

**Trigger**: Authenticated user calls an AI action.
**Steps**: Backend reads user.plan from DB → if "pro", skip usage check → action proceeds.
**Duration class**: Immediate (adds < 5ms to any AI action).
**Failure shape**: If plan lookup fails → action proceeds as free-tier (fail-safe).
