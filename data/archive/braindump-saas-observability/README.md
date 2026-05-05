# spec-doc — SaaS Observability (Sentry + structlog + health checks + JSON errors)

> **MERGED** into `braindump-saas-operations.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P3 — ship around Phase 1 so the rest of the SaaS migration is debuggable.
> **Effort**: ~1.5 days (Sentry + structlog + 3 health checks + error handler).
> **Blocks**: nothing structurally; **enables** debugging every other bucket once it lands.
> **Depends on**: nothing — pure additive infrastructure.
> **Siblings**: every other bucket — observability is the lens through which everything is monitored.
> **Bundles**: capabilities #19 (centralised JSON error handler), #45 (Sentry), #46 (structlog), #47 (per-external-dep health checks) — four small items that share a module.
> **Port from**: bubls (Sentry SDK + structlog config + per-dep `BaseRestApiHealthCheck` pattern). Near-verbatim.

## What

Four small operational concerns, all in one new module (`api/modules/observability/`), so the SaaS deploy is debuggable without each future feature reinventing logging or hand-rolling its own error handler. Bubls ships every one of these in production; spec-doc is currently flying blind on all four.

1. **Sentry SDK** for unhandled exceptions in Flask + Angular, scoped to user when auth is loaded.
2. **structlog with JSON output** — every log line carries `request_id`, `user_id`, `feature`, structured key-value context.
3. **Per-external-dep health checks** — `/api/health/anthropic`, `/api/health/supabase`, `/api/health/stripe`. Coolify can poll these to surface degraded-dependency state.
4. **Centralised JSON error handler** — every uncaught exception returns `{error, code, request_id}` instead of HTML stack traces.

### 1. Sentry — `modules/observability/sentry.py`

```python
"""Sentry SDK initialisation. Loaded by create_app() at startup."""
import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

def init_sentry(app):
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        app.logger.info("SENTRY_DSN not set — error tracking disabled")
        return
    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.environ.get("APP_ENV", "production"),
        release=os.environ.get("APP_RELEASE", "dev"),
    )
```

Per-request user scoping happens in the auth middleware — after `g.current_user` is set, `sentry_sdk.set_user({"id": g.current_user.id, "email": g.current_user.email})`. Anonymous requests stay anonymous.

Angular gets `@sentry/angular` configured in `main.ts` with the same DSN (different project in the Sentry dashboard, or `tags: {component: 'frontend'}` to split). 5 lines of frontend init.

### 2. structlog — `modules/observability/logging.py`

```python
import logging
import os
import structlog
from flask import g, has_request_context, request

def init_logging():
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            _add_request_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level, format="%(message)s")


def _add_request_context(logger, method_name, event_dict):
    """Inject request_id, user_id, feature into every log call."""
    if not has_request_context():
        return event_dict
    event_dict["request_id"] = request.headers.get("X-Request-ID") or _gen_id()
    if hasattr(g, "current_user") and g.current_user:
        event_dict["user_id"] = g.current_user.id
    return event_dict
```

Every module switches `import logging; logger = logging.getLogger(__name__)` to `import structlog; logger = structlog.get_logger(__name__)`. Existing `logger.info("foo")` calls still work; the new structured form is `logger.info("event_name", extra_field=value)`.

The CI smoke test asserts the log output is JSON — one `json.loads()` on the captured stderr.

### 3. Per-external-dep health checks — `modules/observability/health.py`

```python
"""Per-dep health probes. Each is a 200 if reachable, 503 if degraded."""
from flask import Blueprint, jsonify
import os, time, requests
from anthropic import Anthropic

health_bp = Blueprint("health", __name__, url_prefix="/api/health")


@health_bp.get("/anthropic")
def anthropic_health():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"status": "skipped", "reason": "no key"}), 200
    try:
        client = Anthropic(timeout=5.0)
        client.messages.count_tokens(model="claude-haiku-4-5", messages=[{"role": "user", "content": "ping"}])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)[:100]}), 503


@health_bp.get("/supabase")
def supabase_health():
    url = os.environ.get("SUPABASE_URL")
    if not url:
        return jsonify({"status": "skipped"}), 200
    try:
        r = requests.get(f"{url}/auth/v1/health", timeout=5)
        return (jsonify({"status": "ok"}), 200) if r.ok else (jsonify({"status": "degraded"}), 503)
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)[:100]}), 503


@health_bp.get("/stripe")
def stripe_health():
    if not os.environ.get("STRIPE_SECRET_KEY"):
        return jsonify({"status": "skipped"}), 200
    try:
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        stripe.Account.retrieve()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)[:100]}), 503
```

Each check is cheap (one API call, 5s timeout). Coolify or any uptime monitor (UptimeRobot, BetterUptime) polls these and pages the on-call when one degrades. The existing `/health` route stays as the liveness probe (process is up); the new ones are readiness probes (deps reachable).

### 4. Centralised JSON error handler — `modules/observability/errors.py`

```python
"""Centralised error responses. All uncaught errors return JSON, not HTML."""
import structlog
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from pydantic import ValidationError

logger = structlog.get_logger(__name__)


def register_error_handlers(app):

    @app.errorhandler(HTTPException)
    def handle_http(exc):
        return jsonify({"error": exc.description, "code": exc.code}), exc.code

    @app.errorhandler(ValidationError)
    def handle_validation(exc):
        return jsonify({"error": "validation_failed", "details": exc.errors()}), 422

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        logger.exception("unhandled_exception", path=request.path)
        # Sentry catches it via the FlaskIntegration; we just shape the user response
        return jsonify({"error": "internal_server_error", "code": 500}), 500
```

Wired into `create_app()` as the last step. Replaces every per-module `try/except + jsonify({"error": ...}), 500` with one consistent shape.

### 5. .env additions

```
SENTRY_DSN=https://...@sentry.io/...
SENTRY_TRACES_SAMPLE_RATE=0.1
APP_ENV=production            # tags Sentry events; "development" / "staging" / "production"
APP_RELEASE=spec-doc@1.0.0    # Sentry release tracking; CI sets to git SHA
LOG_LEVEL=INFO
```

### 6. Wiring in `create_app.py`

```python
def create_app(config=None):
    app = Flask(__name__)
    init_logging()                       # structlog first — logs from below
    init_sentry(app)                     # Sentry — captures everything from here on
    register_error_handlers(app)         # JSON error responses
    app.register_blueprint(health_bp)    # /api/health/* readiness probes
    # ... existing blueprints
    return app
```

### 7. Tests

```python
def errorHandler_returnsJsonNotHtml(client):
    @app.route("/test/boom")
    def boom():
        raise RuntimeError("oops")
    r = client.get("/test/boom")
    assert r.status_code == 500
    assert r.is_json
    assert r.get_json()["error"] == "internal_server_error"


def healthAnthropic_returnsSkippedWhenKeyAbsent(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.get("/api/health/anthropic")
    assert r.status_code == 200
    assert r.get_json()["status"] == "skipped"


def structlog_emitsJsonWithRequestId(client, capsys):
    client.get("/health", headers={"X-Request-ID": "abc-123"})
    line = capsys.readouterr().err.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["request_id"] == "abc-123"
```

## Why now

The SaaS migration adds three external dependencies (Anthropic SDK, Supabase, Stripe) that were not in the dev tool. Each can degrade independently. Without health checks the team learns Stripe is down by reading user complaints, not by paging on it. Without Sentry the team sees the 500 in the user's screenshot before seeing it in their own logs. Without structlog the deploy logs are unparseable noise.

These four items always ship together in bubls because they share a debug-context model: same `request_id` flows through structured logs, error responses, and Sentry events. Splitting them across four brain dumps would obscure that they're one operational story.

The bubls port is genuinely cheap — each piece is ~10–30 LOC. The cost is the project setup (Sentry account, DSN provisioning, log aggregator destination if any). Most of that is one-time admin work, not engineering.

## What's missing

Two decisions:

1. **Where do JSON logs go in production?** Options:
   - (a) Coolify captures stdout (proposed) — zero infra; logs viewable in Coolify UI; not searchable across time
   - (b) Ship to a log aggregator (BetterStack / Logtail / Grafana Loki) — searchable, alertable; costs money + setup
   - (c) Self-hosted Loki — cheapest at scale; operational burden

   (a) is right for v1. Add (b) when deploy volume justifies it.

2. **Sentry traces sample rate** — proposed 0.1 (10% of requests get a trace). Trade-off: more samples = better insight + higher Sentry cost. 0.1 matches bubls's launch config.

## Explicitly out of scope

- **APM (Datadog, New Relic) instrumentation** — Sentry covers errors + basic perf; full APM is enterprise-tier infra.
- **Custom metrics dashboard** — `/api/stats` endpoint (cost dashboard, in the SDK provider brain dump) covers product metrics; ops metrics belong in Sentry/Coolify.
- **OpenTelemetry tracing** — overkill for a single-service backend; reconsider if/when the architecture splits.
- **Per-tenant log isolation** — `user_id` is in every log line; aggregator filtering is the access control.
- **Audit log of admin actions** — separate concern; brain dump when admin tools (capability #75) are scoped.
- **PII scrubbing in logs** — structlog config can add a processor; not needed until a compliance trigger fires.
- **Frontend session replay (Sentry Replay)** — adds payload size; turn on when first hard-to-repro user bug appears.
