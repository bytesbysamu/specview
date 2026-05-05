
```markdown
---
sidebar_position: 4
---

# 📅 Modular Photoshoot Modes – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Prompt config module | backlog | `server/modules/photoshoot/prompts.py` — extract Trendfy prompts from wardrobai repo |
| 2 | OpenAPI + DTO update | backlog | Add `mode` enum + `custom_style` field, regen types |
| 3 | Backend mode resolution | backlog | Replace hardcoded template in service.py |
| 4 | Frontend mode picker | backlog | `ion-segment` on photoshoot page + custom textarea |
| 5 | Integration test + TestFlight QA | backlog | Backend unit tests + manual device verification |

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-17 | — | Epic created | 5 tasks, ~1.5 days total effort |
```

---

5 files, all grounded in the actual codebase. Key decisions made:

| Decision | Choice |
|---|---|
| 5 Trendfy scenarios | Collapsed into one "outfit" mode with `random.choice` |
| Mode picker UX | `ion-segment` (3 buttons: portrait / outfit / custom) |
| Custom guardrails | Freeform, 500 char max, no moderation for TestFlight |
| Style storage | Python config dict, not database |
| Negative prompt | Shared across all modes, not per-mode |
| `default_style_prompt` column | Stays in schema, service stops reading it |