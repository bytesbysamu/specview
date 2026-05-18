---
name: No direct code edits — go through braindump workflow
description: User wants all non-trivial changes planned via braindump project before any code is touched
type: feedback
---

Do not apply code changes directly when the user describes a feature or improvement. Instead:
1. Create a braindump project in `data/projects/` with a timestamped ID
2. Write a `braindump.md` capturing the request in full detail
3. Let the user run `/spec-pipeline` or ask to proceed before touching any code

**Why:** User wants to review the plan (implementation guide) before execution, and wants changes to go through the tracked exec-guide flow for auditability.

**How to apply:** Any time the user describes UI improvements, new features, or refactors — even small ones — stop before editing files. Create the braindump project first.
