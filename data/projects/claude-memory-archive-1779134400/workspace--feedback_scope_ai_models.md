---
name: Scope for ai-models work
description: When working in /workspace/ai-models/, stay on backend/model pipeline only — don't bring frontend/app concerns into scope
type: feedback
---

In `/workspace/ai-models/`, my scope is **backend and model pipeline only**.

**Why:** The repo has separate agents/workspaces for landing (`/workspace/landing/`), app (`/workspace/app/`), and ai-models. When the user asks me to work in ai-models, they don't want me pulling app integration concerns (Angular routes, frontend status states, UI flows) into my plans or implementations. The app agent owns that side.

**How to apply:** When planning or implementing in ai-models:
- Focus on: portable Python functions, notebook cells, Replicate/Anthropic calls, JSON schemas, per-user outputs
- Skip: Angular routes, frontend API contracts beyond a minimal JSON return shape, UI state machines, i18n concerns (unless the user explicitly adds them to the plan)
- If the user's plan edits add frontend/app context, treat it as informational — don't extend it unprompted
