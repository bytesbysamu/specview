---
name: dev-build
description: "Build the specview API (pytest dry-run) or Angular frontend (ng build). Auto-detects stack from cwd. Reports errors, never auto-fixes."
---

# /dev-build — Build check

Run the build/type-check for the detected stack.

## STOP — Read first

Never auto-fix build errors. Report and stop.

## Stack Detection

Detect from cwd:
- Contains `web-ng/` or `angular.json` in the path → **frontend**
- Contains `api/` or `conftest.py` in the path → **backend**
- At repo root → ask the user which stack.

## Procedure

### Backend (api/)

```bash
cd /path/to/specview/api
python -m pytest --collect-only -q 2>&1 | head -20
```

Confirms import graph is intact. For a deeper check:

```bash
python -c "import api.app"
```

### Frontend (web-ng/)

```bash
cd /path/to/specview/web-ng
npx ng build --configuration production 2>&1 | tail -30
```

## Output Format

**Success:**
```
Build: ok (backend)
Collected: N tests
```

**Failure:**
```
Build: FAILED (frontend)
Errors:
  - src/app/app.component.ts:42 — Property 'x' does not exist on type 'Y'
```

Stop after reporting. Do not attempt fixes.

## Allowed Tools

Bash, Read, Glob, Grep
