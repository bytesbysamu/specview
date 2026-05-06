# Flask / Litestar Backend Conventions — spec-doc / specview

This reference describes the backend API conventions for `api/modules/`.
All agents and skills that touch Flask route code must read this file first.

## Module Structure

Each feature module lives under `api/modules/{name}/` and contains:

```
api/modules/{name}/
├── __init__.py
├── models.py       — SQLModel table models
├── routes/
│   └── {name}.py   — Flask Blueprint with routes
└── tests/
    └── test_{name}.py
```

Flat-file convention — no sub-packages inside a module unless explicitly approved.
Routes export a single `Blueprint` named `{name}_bp`.

## Blueprint Registration

Blueprints are registered in `api/app.py`. The prefix is `/api/{feature}`.
Example:

```python
from modules.ai.routes.task_gen import task_gen_bp
app.register_blueprint(task_gen_bp, url_prefix="/api/projects")
```

## Route Decorators

Two mandatory decorators for protected routes:

- `@require_auth` — validates JWT from `Authorization: Bearer <token>` header.
  Returns 401 if missing or invalid.
- `@check_usage_limit("scope")` — enforces per-user rate limits for AI-heavy routes.
  Returns 429 if limit exceeded.

Order: `@bp.post(...)`, then `@require_auth`, then `@check_usage_limit(...)`.
Never reverse this order — `require_auth` must run before usage checks.

## Error Responses

Use `APIError(message, status_code)` for user-facing errors. Never return raw
error strings from route handlers. Format:

```python
raise APIError("Project not found", 404)
```

The global error handler converts `APIError` to `{"error": message}` JSON.
`ProviderError` bubbles up through the chain adapter and is caught by the
global handler as a 502 or 504.

## SQLModel Patterns

Route handlers never touch the database directly. Flow:

1. Route handler validates input (Pydantic or manual).
2. Calls a service function in `modules/{name}/services/`.
3. Service uses `get_session()` session dependency.
4. Returns a SQLModel instance or a dict for JSON serialization.

Never call `session.commit()` inside a route handler.
Service functions own the transaction boundary.

## Project File Conventions

Projects store generated spec files under `SPEC_DOC_DIR/{project_id}/`.
The `SPEC_DOC_DIR` env var is `/data/spec-doc` in Docker.
File reads/writes use plain `pathlib.Path` — no abstraction layer.

Spec filenames are fixed:
- `braindump.md` — user's raw input
- `analysis.md` — generated analysis
- `epic.md` — generated epic
- `architecture.md` — generated architecture
- `timeline.md` — generated timeline
- `implementation-guide.md` — generated guide

## Authentication

JWT secret from `JWT_SECRET` env var. Payload contains `user_id` (UUID string).
`require_auth` decorator sets `g.user_id` for the request lifetime.
Never log `user_id` in plaintext — hash it for log lines.

## Background Jobs

Long-running AI generation runs in a `threading.Thread`.
State is held in a module-level dict (job_id -> status dict).
`snapshot(job_id)` returns `{running, done, error?, files?}`.
Poll endpoints are `GET` routes with no body.

## CORS

`CORS_ORIGINS` env var controls allowed origins. Set to `"*"` in development.
Never hardcode an origin — always read from env.

## Quality Rules (non-negotiable)

- No raw SQL in route handlers.
- No direct `session` usage outside service layer.
- No `print()` — use `logging.getLogger(__name__)`.
- No synchronous blocking calls inside async contexts.
- All AI routes behind `@require_auth` and `@check_usage_limit`.
- Never return a Python exception object as a response body.
