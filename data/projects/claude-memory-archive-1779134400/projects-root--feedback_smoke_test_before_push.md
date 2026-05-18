---
name: Smoke test locally before pushing
description: Always rebuild and smoke test locally before git push — user wants to verify changes work before they go to GitHub/Coolify
type: feedback
---

Always rebuild locally and do a quick smoke test (curl or instruct user to check browser) before running `git push`. Confirm the user is happy with what they see before pushing.

**Why:** User got burned by pushing changes they hadn't verified locally yet.

**How to apply:** After making changes — rebuild with `docker compose up --build -d`, verify the key endpoints/UI work, then ask the user to check before pushing.
