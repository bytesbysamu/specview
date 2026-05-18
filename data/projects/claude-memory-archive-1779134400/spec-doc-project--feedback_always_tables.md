---
name: Status updates always render as tables (dashboard shape)
description: For any live/recurring progress report — agent runs, deployments, test results, commit activity — Sam wants the output rendered as a markdown table, dashboard-style, not prose
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
When surfacing live or repeated status — parallel agent progress, CI state, deviation tallies, per-world feature shipping, anything with a rows × columns shape — **use a markdown table, not prose.**

**Why:** Sam is operating at the architect layer, scanning state across parallel workstreams. A table makes deltas instantly legible; prose buries them. Dashboard shape matches how he reads the work.

**How to apply:**
- Live monitor events → table with one row per task/stream, columns for count / latest / status / note
- Test reports → table with suite × pass/fail/skip
- Deviation tallies → task × count × category
- Batch summaries at end of runs → same shape
- Even single-event updates: if the context is "live dashboard," keep the table shape and add/update a row rather than switching to prose
- Short narrative sentences are fine AFTER the table if there's a judgment call to flag — but the table comes first.
