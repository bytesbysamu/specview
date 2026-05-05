# Task 3: Email Capture Backend

**Purpose**: Standalone Flask microservice that stores email signups in Neon Postgres with per-IP rate limiting, giving the Bubls landing page a backend for its email form.

**Effort**: 2 hours

**Dependencies**: None — runs in Phase 1 parallel with Tasks 1 and 2

**Parallel With**: Task 1 (Domain + DNS), Task 2 (Screenshot capture)

**Blocks**: Task 4 (landing page build needs the `/api/email-signup` endpoint contract), Task 5 (Coolify deploy wires up this service)

**Related**:
- [Architecture — Task 3 Component Design](./architecture.md#task-3-email-capture-backend)
- [Epic — Task 3 Detail](./epic.md#task-3-email-capture-backend)

---

## 1. Context

This task builds a throwaway Flask microservice — one endpoint, one table, one container — that accepts email signups from the Bubls landing page and persists them to the shared Neon Postgres instance. The service is deliberately minimal (~30 lines of application code) because its only job is to capture interest before the app launches. It runs independently of the main Bubls backend (`server/modules/`) and can be deleted without touching any other service. Rate limiting is in-memory (dict keyed by IP, 5 requests/hour) because state loss on restart is acceptable for abuse prevention at pre-launch traffic levels. CORS is restricted to the landing page domain.

**Trade-offs considered**:
- **SQLAlchemy ORM** — rejected for this service. Global principles mandate ORM, but the project architecture (architecture.md lines 76–78) explicitly prescribes `psycopg2-binary` for a ~30-line standalone microservice with one table and one write query. Adding SQLAlchemy + Alembic triples the file count and dependency surface for zero benefit here. This deviation applies ONLY to this standalone landing page service, not to the main Bubls backend (which correctly uses SQLAlchemy).
- **flask-limiter library** — rejected. 8 lines of inline rate limiting beat adding a dependency with its own config surface. The rate limiter is trivial enough to test directly.
- **Neon-backed rate limiting** — rejected. In-memory dict is simpler, and losing state on restart is acceptable per architecture.md Design Decisions.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git log --oneline -5                          # Note HEAD sha for rollback
ls -la email-api/ 2>/dev/null || echo "email-api/ does not exist yet — clean start"
python3 --version                             # Confirm Python 3.10+ available
pip3 install --dry-run flask psycopg2-binary gunicorn pytest 2>&1 | head -5  # Confirm pip resolves deps
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**Baseline recorded**: no pre-existing tests for email-api (new service). Main Bubls backend tests are unaffected.

---

## 3. Files

### To Create (new)
- `email-api/app.py` — Flask app: one endpoint (`POST /api/email-signup`), CORS, rate limiting, email validation, psycopg2 insert
- `email-api/requirements.txt` — `flask`, `flask-cors`, `psycopg2-binary`, `gunicorn`
- `email-api/Dockerfile` — Python 3.12 slim, gunicorn on port 5000
- `email-api/migrate.sql` — `bubls_email_signups` table DDL + indexes
- `email-api/.env.example` — template for `DATABASE_URL` and `ALLOWED_ORIGIN`
- `email-api/tests/__init__.py` — empty, makes `tests/` a package
- `email-api/tests/test_app.py` — 8 pytest tests covering all response codes + rate limiting + email normalization

### To Modify (cite CODEBASE CONTEXT)
- `projects/landing-page-1776432535131/timeline.md` — update Task 3 status from `backlog` to `done`

### To Leave Alone
- `server/` — main Bubls backend; this task creates a separate microservice, not a new module
- `src/` — Angular frontend; no frontend changes in this task
- `projects/landing-page-1776432535131/architecture.md` — architecture is stable; implementation follows it
- `projects/landing-page-1776432535131/epic.md` — scope is stable

---

## 4. Implementation Steps

### Step 1: Create directory structure

**Action**: Create the `email-api/` directory tree.

**File**: `email-api/` (new), `email-api/tests/` (new)

**Pattern**:
```
email-api/
├── app.py
├── requirements.txt
├── Dockerfile
├── migrate.sql
├── .env.example
└── tests/
    ├── __init__.py
    └── test_app.py
```

**Verify**: `ls -R email-api/` — expect the directory tree above (files created in subsequent steps)

---

### Step 2: Write migration SQL

**Action**: Create the table DDL matching architecture.md lines 82–92. This is a file in the repo, not a live migration — it will be run against Neon manually in Step 9.

**File**: `email-api/migrate.sql` (new)

**Pattern**:
```sql
-- Bubls email signups table
-- Run once against Neon Postgres: psql $DATABASE_URL -f migrate.sql

CREATE TABLE IF NOT EXISTS bubls_email_signups (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_signups_email ON bubls_email_signups(email);
CREATE INDEX IF NOT EXISTS idx_email_signups_ip ON bubls_email_signups(ip_address);
```

**Verify**: `cat email-api/migrate.sql` — expect `CREATE TABLE`, `UNIQUE` constraint on email, two indexes, `IF NOT EXISTS` guards

---

### Step 3: Write requirements.txt

**Action**: Pin Flask and psycopg2-binary. No version pins — this is a throwaway service; latest stable is fine.

**File**: `email-api/requirements.txt` (new)

**Pattern**:
```
flask
flask-cors
psycopg2-binary
gunicorn
pytest
```

**Verify**: `pip3 install --dry-run -r email-api/requirements.txt 2>&1 | tail -3` — expect "Would install" or "already satisfied"

---

### Step 4: Write .env.example

**Action**: Template for required environment variables.

**File**: `email-api/.env.example` (new)

**Pattern**:
```
DATABASE_URL=postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/dbname?sslmode=require
ALLOWED_ORIGIN=https://bubls.app
```

**Verify**: `cat email-api/.env.example` — expect two variables, no secrets

---

### Step 5: Write app.py

**Action**: The Flask application. ~30 lines of endpoint code + rate limiting + email validation. Port the Flask factory shape from humanize-me `backend/app.py` (streaming route pattern, lines 182–241 in REFERENCE CODE), adapted for a non-streaming JSON endpoint. CORS origin comes from `ALLOWED_ORIGIN` env var.

**File**: `email-api/app.py` (new)

**Pattern**:
```python
import os
import re
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import errors as pg_errors

app = Flask(__name__)
CORS(app, origins=[os.environ.get("ALLOWED_ORIGIN", "http://localhost:4201")])

DATABASE_URL = os.environ.get("DATABASE_URL")

# In-memory rate limiter: { ip: [timestamp, ...] }
_rate_limits: dict[str, list[float]] = {}
RATE_LIMIT = 5
RATE_WINDOW = 3600  # 1 hour in seconds

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    hits = _rate_limits.get(ip, [])
    hits = [t for t in hits if now - t < RATE_WINDOW]
    _rate_limits[ip] = hits
    if len(hits) >= RATE_LIMIT:
        return True
    hits.append(now)
    return False


def _get_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


@app.route("/api/email-signup", methods=["POST"])
def email_signup():
    ip = _get_ip()
    if _is_rate_limited(ip):
        return jsonify({"error": "Too many requests"}), 429

    data = request.get_json(silent=True)
    if not data or "email" not in data:
        return jsonify({"error": "Invalid email"}), 400

    email = data["email"].strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email"}), 400

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bubls_email_signups (email, ip_address) VALUES (%s, %s)",
            (email, ip),
        )
        conn.commit()
        cur.close()
        conn.close()
    except pg_errors.UniqueViolation:
        return jsonify({"error": "Already signed up"}), 409
    except Exception:
        return jsonify({"error": "Server error"}), 500

    return jsonify({"status": "ok"}), 201


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

**Key implementation notes**:
- Email lowercased before insert — prevents `User@Ex.com` and `user@ex.com` being treated as different signups
- `X-Forwarded-For` header read for IP — Coolify reverse proxy sets this
- `UniqueViolation` caught for 409 — Postgres UNIQUE constraint does the dedup
- `/health` endpoint for Coolify health checks
- Connection opened and closed per request — acceptable at pre-launch traffic. No connection pool needed yet.

**Verify**: `python3 -c "import ast; ast.parse(open('email-api/app.py').read()); print('syntax ok')"` — expect "syntax ok"

---

### Step 6: Write Dockerfile

**Action**: Production container for Coolify deployment.

**File**: `email-api/Dockerfile` (new)

**Pattern**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

**Verify**: `docker build -t bubls-email-api email-api/` — expect successful build (no runtime test yet)

---

### Step 7: Write tests

**Action**: 8 pytest tests using Flask's test client. No database connection needed — mock `psycopg2.connect` to isolate endpoint logic from Neon.

**File**: `email-api/tests/test_app.py` (new)

**Pattern**: See Section 5 (Tests) below for complete assertion bodies.

**Verify**: `cd email-api && DATABASE_URL=postgresql://fake:fake@localhost/fake python3 -m pytest tests/ -v` — expect 8 passed

---

### Step 8: Run tests

**Action**: Execute the test suite locally.

**Verify**: `cd email-api && DATABASE_URL=postgresql://fake:fake@localhost/fake python3 -m pytest tests/ -v --tb=short` — expect `8 passed` with 0 failures

---

### Step 9: Run migration against Neon [REQUIRES APPROVAL]

**Action**: Execute `migrate.sql` against the shared Neon Postgres instance. This creates a real table in production.

```bash
# [REQUIRES APPROVAL] — creates table in production Neon
psql $DATABASE_URL -f email-api/migrate.sql
```

**Verify**: `psql $DATABASE_URL -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'bubls_email_signups' ORDER BY ordinal_position;"` — expect 4 columns (id, email, ip_address, created_at)

---

### Step 10: Smoke test against live database

**Action**: Start the Flask app locally pointing at Neon and test the full round-trip.

```bash
cd email-api && ALLOWED_ORIGIN="*" DATABASE_URL=$DATABASE_URL python3 app.py &
sleep 2

# Test valid signup
curl -s -X POST http://localhost:5000/api/email-signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test-smoke@example.com"}' | python3 -m json.tool

# Expect: { "status": "ok" } with HTTP 201

# Test duplicate
curl -s -w "\n%{http_code}" -X POST http://localhost:5000/api/email-signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test-smoke@example.com"}'

# Expect: 409

# Cleanup
psql $DATABASE_URL -c "DELETE FROM bubls_email_signups WHERE email = 'test-smoke@example.com';"
kill %1
```

**Verify**: 201 on first call, 409 on duplicate, row appears and is cleaned up

---

### Step 11: Update timeline

**Action**: Mark Task 3 as done in the timeline.

**File**: `projects/landing-page-1776432535131/timeline.md`

**Pattern**: Change Task 3 row status from `backlog` to `done`, add completion date.

**Verify**: `grep "Task 3" projects/landing-page-1776432535131/timeline.md` — expect `done`

---

## 5. Tests

All tests use Flask's test client and mock `psycopg2.connect`. Framework: pytest (matches the Bubls backend test setup in `server/tests/`).

```python
"""Tests for email-signup endpoint."""
import time
from unittest.mock import patch, MagicMock

import pytest
from psycopg2 import errors as pg_errors

# Set DATABASE_URL before importing app (app reads it at module level)
import os
os.environ.setdefault("DATABASE_URL", "postgresql://fake:fake@localhost/fake")

from app import app, _rate_limits


@pytest.fixture
def client():
    app.config["TESTING"] = True
    _rate_limits.clear()
    with app.test_client() as c:
        yield c


@pytest.fixture
def mock_db():
    with patch("app.psycopg2.connect") as mock_conn:
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        mock_conn.return_value = conn
        yield {"connect": mock_conn, "conn": conn, "cursor": cur}


class TestEmailSignup:
    def test_validEmail_returns201(self, client, mock_db):
        res = client.post(
            "/api/email-signup",
            json={"email": "user@example.com"},
        )
        assert res.status_code == 201
        assert res.get_json() == {"status": "ok"}
        mock_db["cursor"].execute.assert_called_once()
        # Verify email was lowercased in the INSERT
        call_args = mock_db["cursor"].execute.call_args[0]
        assert call_args[1][0] == "user@example.com"

    def test_missingBody_returns400(self, client):
        res = client.post(
            "/api/email-signup",
            content_type="application/json",
            data="",
        )
        assert res.status_code == 400
        assert "Invalid email" in res.get_json()["error"]

    def test_missingEmailField_returns400(self, client):
        res = client.post(
            "/api/email-signup",
            json={"name": "not an email field"},
        )
        assert res.status_code == 400
        assert "Invalid email" in res.get_json()["error"]

    def test_invalidEmailFormat_returns400(self, client):
        res = client.post(
            "/api/email-signup",
            json={"email": "not-an-email"},
        )
        assert res.status_code == 400
        assert "Invalid email" in res.get_json()["error"]

    def test_duplicateEmail_returns409(self, client, mock_db):
        mock_db["cursor"].execute.side_effect = pg_errors.UniqueViolation()
        res = client.post(
            "/api/email-signup",
            json={"email": "dupe@example.com"},
        )
        assert res.status_code == 409
        assert "Already signed up" in res.get_json()["error"]

    def test_rateLimitExceeded_returns429(self, client, mock_db):
        for i in range(5):
            res = client.post(
                "/api/email-signup",
                json={"email": f"user{i}@example.com"},
            )
            assert res.status_code == 201, f"Request {i+1} should succeed"

        res = client.post(
            "/api/email-signup",
            json={"email": "user5@example.com"},
        )
        assert res.status_code == 429
        assert "Too many requests" in res.get_json()["error"]

    def test_emailNormalized_lowercased(self, client, mock_db):
        res = client.post(
            "/api/email-signup",
            json={"email": "  User@EXAMPLE.COM  "},
        )
        assert res.status_code == 201
        call_args = mock_db["cursor"].execute.call_args[0]
        assert call_args[1][0] == "user@example.com"

    def test_rateLimitResetsAfterWindow(self, client, mock_db):
        # Fill the rate limit
        for i in range(5):
            client.post(
                "/api/email-signup",
                json={"email": f"user{i}@example.com"},
            )

        # Verify limited
        res = client.post(
            "/api/email-signup",
            json={"email": "blocked@example.com"},
        )
        assert res.status_code == 429

        # Simulate window expiry by backdating timestamps
        ip = "127.0.0.1"
        _rate_limits[ip] = [time.time() - 3601 for _ in _rate_limits.get(ip, [])]

        res = client.post(
            "/api/email-signup",
            json={"email": "unblocked@example.com"},
        )
        assert res.status_code == 201
```

---

## 6. Commit Plan

One commit per logical unit:

1. **`feat(email-api): add email capture microservice`** — `email-api/app.py`, `email-api/requirements.txt`, `email-api/Dockerfile`, `email-api/migrate.sql`, `email-api/.env.example`: Flask endpoint + container + schema
2. **`test(email-api): add pytest suite for email signup endpoint`** — `email-api/tests/__init__.py`, `email-api/tests/test_app.py`: 8 tests covering all response codes, rate limiting, email normalization
3. **`docs(landing-page): mark task 3 done in timeline`** — `projects/landing-page-1776432535131/timeline.md`: status `backlog` → `done`

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation. Example:
```
Deviations:
- Used flask-limiter instead of inline rate limiter (psycopg2 connection sharing required it)
```

---

## 7. Verification

```bash
cd email-api && DATABASE_URL=postgresql://fake:fake@localhost/fake python3 -m pytest tests/ -v --tb=short
```

**Expected delta**: 0 → 8 passing. Zero pre-existing tests broken (this is a new, isolated service).

Optional integration check (if Neon `DATABASE_URL` is available):
```bash
cd email-api && ALLOWED_ORIGIN="*" DATABASE_URL=$DATABASE_URL python3 -c "
from app import app
with app.test_client() as c:
    r = c.get('/health')
    assert r.status_code == 200, f'Health check failed: {r.status_code}'
    print('Health check passed')
"
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any of the 3 commits.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (the HEAD sha recorded in Pre-flight).
- **Database**: if migrate.sql was run against Neon, rollback with:
  ```bash
  # [REQUIRES APPROVAL] — drops production table
  psql $DATABASE_URL -c "DROP TABLE IF EXISTS bubls_email_signups;"
  ```

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in architecture.md; if still missing, create it and note the deviation in the commit body.
- **psycopg2 connection behavior differs** → if `psycopg2.connect` fails in the test mock setup, adjust the mock patching path but keep the same test assertions. Log the deviation.
- **`X-Forwarded-For` header format differs under Coolify** → adapt `_get_ip()` to handle the actual header format. The rate limiter's correctness doesn't depend on perfect IP extraction — it's abuse prevention, not billing.
- **Python version < 3.12** → the `dict[str, list[float]]` type hint requires 3.9+. If running 3.8, change to `Dict[str, List[float]]` from `typing`. Log as deviation.
- **Side-effect required** (run migration, push, publish) → STOP, mark `[REQUIRES APPROVAL]` and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task builds the Flask microservice and its tests. It does NOT cover deployment, frontend integration, or email sending — those are downstream tasks with their own guides.

- **Coolify deployment** — Task 5 handles Docker container deployment, reverse proxy config, and environment variable injection. Do not configure Coolify in this task.
- **Frontend email form** — Task 4 builds the `<form>` that calls this endpoint. The endpoint contract (architecture.md lines 97–106) is stable; Task 4 codes against it.
- **CORS domain finalization** — `ALLOWED_ORIGIN` defaults to `http://localhost:4201` for local dev. Task 5 sets the production value (`https://bubls.app`) via Coolify env vars. If Task 1 chooses a different domain, update `.env.example` but the app reads from the env var at runtime.
- **Email sending / drip sequences** — explicitly excluded by epic.md Non-Goals. Capture first, send later.
- **Connection pooling** — a single `psycopg2.connect` per request is fine at pre-launch traffic. Add pooling (e.g., `psycopg2.pool.SimpleConnectionPool`) only if response times degrade under load.
- **Email verification / double opt-in** — excluded per epic.md Non-Goals.
- **Analytics or signup count dashboard** — "Not-yet-built is the right state" (architecture.md Design Principles). Query Neon directly (`SELECT COUNT(*) FROM bubls_email_signups`) when needed.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture — Task 3 Component Design](./architecture.md#task-3-email-capture-backend) — schema, endpoint contract, rate limiting decision
- [Epic — Task 3 Detail](./epic.md#task-3-email-capture-backend) — scope definition
- [Timeline](./timeline.md) — update status after done
- Architecture Design Decisions — "Flask vs adding to existing backend" row justifies standalone microservice
- Architecture Design Decisions — "Rate limiting approach" row justifies in-memory over Redis/Neon

---

##### Post-generation review (auto)

**Overall**: 5/5 (gold)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 5/5 | All required sections for a task spec are present and well-organized: Context, Pre-flight, Files, Implementation Steps, Tests, Commit Plan, Verification, Rollback, Deviations Allowed, Out of Scope, Related Documents |
| Content routing | 4/5 | Section 1 Context restates three architectural trade-off decisions (SQLAlchemy, flask-limiter, Neon-backed rate limiting) that originate in architecture.md — should cross-reference rather than duplicate the reasoning. The spec already cites 'architecture.md lines 76–78' but then re-argues the case inline. |
| Pattern application | 4/5 | Trade-offs in Section 1 use bullet-point prose instead of a Decision Justification Table with columns (Option | Chosen | Trade-off | Reason) — the pattern is partially applied but not in canonical table form |
| Rule compliance | 5/5 | Status correctly routed to Timeline only — Step 11 updates timeline.md, no status tracking in this spec |
| Content quality | 5/5 | Highly opinionated and specific — rejects SQLAlchemy, flask-limiter, and Neon-backed rate limiting with concrete reasoning, not hand-waving |
| Usefulness | 5/5 | Fully implementable as-is — every step has Action, File, Pattern (with code), and Verify (with exact shell commands) |

**Top fixes**:
- Fix connection leak in app.py: wrap psycopg2 usage in a try/finally or use `with psycopg2.connect(DATABASE_URL) as conn:` to ensure cleanup on UniqueViolation and generic Exception paths
- Replace the three trade-off bullets in Section 1 with a cross-reference to architecture.md Design Decisions table — state the CHOSEN option and cite the architecture doc for the full reasoning instead of restating it
- Add a fallback path for Steps 9-10 when Neon DATABASE_URL is not available to the executor (e.g., 'skip Steps 9-10, mark as pending in commit body, Task 5 will validate during deployment')
