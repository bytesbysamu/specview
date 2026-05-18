---
name: Always restart services and test integration after backend/route changes
description: When shipping changes that alter routes/schemas/server code, restart the running server and verify end-to-end integration before declaring done
type: feedback
originSessionId: dec008a7-71a7-4fe7-9873-20655fafdd7b
---
After every commit that touches server routes, OpenAPI, or module registration, **restart the running service and hit the new surface end-to-end** before claiming the task is done.

**Why:** In the bubls Task 5 run I committed `PUT /api/user/builder` + `POST /api/user/onboarding/skip` and left the already-running Flask backend unrestarted. The user saw `OPTIONS /api/user/builder → 404` in the browser because Flask doesn't auto-reload without `--reload`/`--debug`. Unit tests were green (they use their own app factory), but the actual service was stale. Shipping a feature the user can't exercise wastes their time.

**How to apply:**
- Start long-running dev servers with auto-reload flags when available (`flask run --reload`, `ng serve` watches by default, `nodemon`, etc.).
- After any commit that adds/changes routes, OpenAPI schemas, middleware, or module imports: kill the old process and start fresh if auto-reload isn't configured. Don't trust "it compiled" as proof the running service has it.
- Once restarted, run a real integration probe — preflight check + actual request — before reporting the step complete. `curl -I` or a single-line `curl -X METHOD` against the live service, not against tests.
- If a background service can't be restarted safely (running client is mid-work), flag it explicitly rather than silently leave it stale.
