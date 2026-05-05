# Task 2: Billing Module — Implementation Guide

## 1. Context

This task creates `modules/billing/` as a Flask Blueprint — the sole writer of `Subscription` rows and `User.plan` state. It also introduces SQLModel + SQLite as spec-doc's first persistence layer; in-process dicts are unsuitable here because subscription state must survive server restarts and Stripe webhook retries require atomic upserts. The module follows ELA #2 exactly: `routes.py` handles HTTP, `service.py` owns all Stripe SDK calls (the billing adapter boundary), `repository.py` owns all DB access, and `models.py` declares the two SQLModel entities. A minimal `modules/auth/decorators.py` stub is created to supply `g.current_user` for the two auth-gated routes; it reads `X-User-Id`/`X-User-Email` headers when `AUTH_BYPASS=true` and validates a JWT otherwise — this stub is explicitly flagged for replacement in a future auth epic.

**Trade-offs considered:**
- File-backed JSON for subscription state — rejected: Stripe's retry policy can deliver events concurrently; SQLite atomic upsert handles this correctly at zero infra cost.
- Separate `adapter.py` for Stripe mirroring `modules/chain/adapter.py` — rejected: ELA #2 explicitly scopes `service.py` as the Stripe boundary for blueprint modules; a second layer would be indirection without a second consumer.
- Webhook-only plan writer vs. in-app plan promotion on checkout success redirect — rejected: in-app write creates a race condition between the checkout redirect and the async webhook; webhook-only is proven correct in bubls production.

---

## 2. Pre-flight

```bash
# Run from {WORKSPACE}/spec-doc/api/

git status                                                # flag any unrelated M/?? entries
git diff HEAD -- create_app.py config.py openapi.yaml requirements.txt
python -m pytest --tb=short -q                           # baseline — record pass count

# Verify Task 1 (OpenAPI contract) is committed:
grep -n "billing" openapi.yaml || echo "STOP: Task 1 not complete — billing paths missing"
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**If `grep` returns nothing**: Task 1 has not shipped. The executor must complete Task 1 (add billing paths and schemas to `openapi.yaml`, run `make generate-dtos`) before proceeding. Step 1 of this guide covers the minimum OpenAPI additions required; complete them as part of Task 1 before committing Step 1 here.

**Baseline recorded**: 624 / 625 passing (1 skip is expected — web-root check).

---

## 3. Files

### To Create (new)
- `api/db.py` — SQLModel engine singleton + `get_session()` context manager + `create_db_and_tables()`; imported by `modules/billing/repository.py` and (Task 3) `modules/usage/repository.py`
- `api/modules/billing/__init__.py` — empty package marker
- `api/modules/billing/models.py` — `User` and `Subscription` SQLModel table classes; table names `spec_doc_users` / `spec_doc_subscriptions`
- `api/modules/billing/repository.py` — `SubscriptionRepository`; methods: `get_for_user`, `get_by_stripe_customer_id`, `get_by_stripe_subscription_id`, `upsert_from_event`, `upsert_from_event_with_plan`, `get_or_create_user`
- `api/modules/billing/service.py` — sole Stripe import point; `create_checkout_session`, `create_portal_session`, `get_or_create_stripe_customer`, `handle_webhook`, `BillingSignatureError`; six `_register`-decorated webhook handlers
- `api/modules/billing/routes.py` — `billing_bp` Blueprint, three handlers: `POST /api/billing/create-checkout-session`, `POST /api/billing/webhook`, `GET /api/billing/status`
- `api/modules/billing/tests/__init__.py` — empty
- `api/modules/billing/tests/conftest.py` — in-memory SQLite fixture; patches `db.get_session` for full test isolation
- `api/modules/billing/tests/test_repository.py` — 6 repository unit tests
- `api/modules/billing/tests/test_service.py` — 6 service/handler unit tests
- `api/modules/billing/tests/test_routes.py` — 7 route-level tests with mocked Stripe
- `api/modules/auth/__init__.py` — empty package marker
- `api/modules/auth/decorators.py` — `require_auth` decorator; `_CurrentUser` named-tuple; `_verify_jwt` stub (HS256 via python-jose)

### To Modify (cite CODEBASE CONTEXT)
- `api/openapi.yaml` — add three billing paths (`/api/billing/create-checkout-session`, `/api/billing/webhook`, `/api/billing/status`) and three schemas (`CheckoutSessionResponse`, `WebhookAckResponse`, `BillingStatusResponse`) — then run `make generate-dtos`
- `api/create_app.py` — add `('modules.billing.routes', 'billing_bp')` to `ENABLED_MODULES`; add `create_db_and_tables()` call in app factory (after blueprint registration)
- `api/config.py` — add five env-var reads: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `FRONTEND_URL`, `DATABASE_URL`
- `api/requirements.txt` — add `stripe>=7.0.0`, `sqlmodel>=0.0.18`, `python-jose[cryptography]>=3.3.0`

### To Leave Alone
- `api/dtos/models.py` — generated; only `make generate-dtos` writes it
- `api/modules/chain/adapter.py` — AI adapter; billing has no AI calls; do not touch
- `api/modules/ai/routes.py` — `@check_usage_limit` application is Task 3 scope; do not pre-empt
- `api/tests/conftest.py` — root fixtures are used by all existing tests; billing-specific fixtures go in `modules/billing/tests/conftest.py`
- `api/modules/task_gen/service.py` — STATE dict; no intersection with billing

---

## 4. Implementation Steps

### Step 1: Extend OpenAPI contract and regenerate DTOs

**Action**: Add billing paths and schemas to `openapi.yaml`, then run `make generate-dtos`. Commit `dtos/models.py` with `git add -f dtos/models.py`.

**File**: `api/openapi.yaml` (existing — CODEBASE CONTEXT)

**Pattern** — append under `paths:`:
```yaml
  /api/billing/create-checkout-session:
    post:
      operationId: createCheckoutSession
      summary: Create a Stripe Checkout session for the Pro plan
      tags: [billing]
      responses:
        '200':
          description: Checkout redirect URL
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CheckoutSessionResponse'
        '401':
          description: Unauthorized

  /api/billing/webhook:
    post:
      operationId: handleBillingWebhook
      summary: Receive signed Stripe webhook events (no auth — Stripe signature required)
      tags: [billing]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              additionalProperties: true
      responses:
        '200':
          description: Event acknowledged
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WebhookAckResponse'
        '400':
          description: Invalid Stripe signature

  /api/billing/status:
    get:
      operationId: getBillingStatus
      summary: Get plan, status, and Customer Portal URL
      tags: [billing]
      responses:
        '200':
          description: Billing status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BillingStatusResponse'
        '401':
          description: Unauthorized
```

**Pattern** — append under `components/schemas:`:
```yaml
    CheckoutSessionResponse:
      type: object
      required: [url]
      properties:
        url:
          type: string

    WebhookAckResponse:
      type: object
      required: [received]
      properties:
        received:
          type: boolean

    BillingStatusResponse:
      type: object
      required: [plan, status]
      properties:
        plan:
          type: string
          enum: [free, pro]
        status:
          type: string
          enum: [active, past_due, canceled, inactive]
        current_period_end:
          type: string
          format: date-time
          nullable: true
        manage_url:
          type: string
          nullable: true
```

**Verify**:
```bash
cd api && make generate-dtos && make check-dtos
grep -n "CheckoutSessionResponse\|BillingStatusResponse\|WebhookAckResponse" dtos/models.py
```
Expect all three class names present in `dtos/models.py`.

---

### Step 2: Create database engine module

**Action**: Create `api/db.py` as the single engine entry point; lazy-init the engine so tests can patch `DATABASE_URL` before first call.

**File**: `api/db.py` (new)

**Pattern**:
```python
import os
from contextlib import contextmanager
from sqlmodel import create_engine, SQLModel, Session

DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///spec_doc.db")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        _engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
    return _engine


def create_db_and_tables() -> None:
    """Import models here so SQLModel.metadata is populated before create_all."""
    from modules.billing.models import User, Subscription  # noqa: F401
    SQLModel.metadata.create_all(_get_engine())


@contextmanager
def get_session():
    with Session(_get_engine()) as session:
        yield session
```

**Verify**:
```bash
cd api && python -c "from db import create_db_and_tables; print('db.py OK')"
```
Expect `db.py OK` with no import errors.

---

### Step 3: Create SQLModel entities

**Action**: Create `api/modules/billing/models.py` with `User` and `Subscription` table classes. Table names use the `spec_doc_*` prefix (ported from bubls `billing/models.py` with `superapp_*` → `spec_doc_*` substitution).

**File**: `api/modules/billing/models.py` (new)

**Pattern**:
```python
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "spec_doc_users"

    id: str = Field(primary_key=True)
    email: str = Field(default="")
    plan: str = Field(default="free")   # "free" | "pro" — written only by billing webhooks


class Subscription(SQLModel, table=True):
    __tablename__ = "spec_doc_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)
    stripe_price_id: Optional[str] = Field(default=None)
    plan: str = Field(default="free")
    status: str = Field(default="inactive")   # active | past_due | canceled | inactive
    current_period_start: Optional[datetime] = Field(default=None)
    current_period_end: Optional[datetime] = Field(default=None)
    canceled_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Verify**:
```bash
cd api && python -c "
from db import create_db_and_tables
create_db_and_tables()
print('tables created OK')
"
```
Expect `tables created OK`. A `spec_doc.db` file will appear in `api/`; this is gitignored (confirm or add to `.gitignore`).

---

### Step 4: Create SubscriptionRepository

**Action**: Create `api/modules/billing/repository.py`. All DB access for the billing module lives here; `service.py` and `routes.py` import only from this class — no direct SQLModel/Session imports elsewhere.

**File**: `api/modules/billing/repository.py` (new)

**Pattern**:
```python
from typing import Optional
from datetime import datetime
from sqlmodel import Session, select

from db import get_session
from .models import Subscription, User


class SubscriptionRepository:

    def get_for_user(self, user_id: str) -> Optional[Subscription]:
        with get_session() as session:
            return session.exec(
                select(Subscription).where(Subscription.user_id == user_id)
            ).first()

    def get_by_stripe_customer_id(self, customer_id: str) -> Optional[Subscription]:
        with get_session() as session:
            return session.exec(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            ).first()

    def get_by_stripe_subscription_id(self, sub_id: str) -> Optional[Subscription]:
        with get_session() as session:
            return session.exec(
                select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
            ).first()

    def upsert_from_event(self, user_id: str, **fields) -> Subscription:
        with get_session() as session:
            return self._upsert_in(session, user_id, **fields)

    def upsert_from_event_with_plan(self, user_id: str, plan: str, **fields) -> Subscription:
        """Upsert Subscription AND write User.plan in a single session."""
        with get_session() as session:
            sub = self._upsert_in(session, user_id, plan=plan, **fields)
            self._write_user_plan(session, user_id, plan)
            session.commit()
            session.refresh(sub)
            return sub

    def get_or_create_user(self, user_id: str, email: str) -> User:
        with get_session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user is None:
                user = User(id=user_id, email=email, plan="free")
                session.add(user)
                session.commit()
                session.refresh(user)
            return user

    # ── private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _upsert_in(session: Session, user_id: str, **fields) -> Subscription:
        sub = session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()
        if sub is None:
            sub = Subscription(user_id=user_id, **fields)
        else:
            for k, v in fields.items():
                setattr(sub, k, v)
            sub.updated_at = datetime.utcnow()
        session.add(sub)
        session.commit()
        session.refresh(sub)
        return sub

    @staticmethod
    def _write_user_plan(session: Session, user_id: str, plan: str) -> None:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user is not None:
            user.plan = plan
            session.add(user)
        # No-op if User row doesn't exist yet — webhook may arrive before first login
```

**Verify**:
```bash
cd api && python -c "
from modules.billing.repository import SubscriptionRepository
print('repository import OK')
"
```

---

### Step 5: Create billing service (Stripe adapter)

**Action**: Create `api/modules/billing/service.py`. This is the **only** file in the codebase that may `import stripe`. Six webhook handlers are registered via a `_register` decorator. `BillingSignatureError` wraps `stripe.error.SignatureVerificationError` so `routes.py` catches the custom exception without importing Stripe directly (ELA #1 adapter boundary).

**File**: `api/modules/billing/service.py` (new)

**Pattern**:
```python
import os
from typing import Optional, Callable, Dict
from datetime import datetime
import stripe

from .repository import SubscriptionRepository

# ── Stripe config (read at module load; never from committed files) ───────────
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
_PRO_PRICE_ID: str = os.environ.get("STRIPE_PRO_PRICE_ID", "")
_FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:4201")

_repo = SubscriptionRepository()
_HANDLERS: Dict[str, Callable] = {}


class BillingSignatureError(Exception):
    """Stripe signature verification failed. Caller returns 400."""


def _register(event_type: str):
    def decorator(fn: Callable) -> Callable:
        _HANDLERS[event_type] = fn
        return fn
    return decorator


# ── public surface ────────────────────────────────────────────────────────────

def get_or_create_stripe_customer(user_id: str, email: str) -> str:
    sub = _repo.get_for_user(user_id)
    if sub and sub.stripe_customer_id:
        return sub.stripe_customer_id
    customer = stripe.Customer.create(email=email, metadata={"user_id": user_id})
    _repo.upsert_from_event(user_id, stripe_customer_id=customer.id)
    return customer.id


def create_checkout_session(user_id: str, email: str) -> str:
    customer_id = get_or_create_stripe_customer(user_id, email)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": _PRO_PRICE_ID, "quantity": 1}],
        success_url=f"{_FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{_FRONTEND_URL}/upgrade",
        metadata={"user_id": user_id},
    )
    return session.url


def create_portal_session(stripe_customer_id: str) -> str:
    portal = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{_FRONTEND_URL}/settings",
    )
    return portal.url


def handle_webhook(payload: bytes, sig_header: str) -> None:
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, _WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as exc:
        raise BillingSignatureError(str(exc)) from exc
    handler = _HANDLERS.get(event["type"])
    if handler is not None:
        handler(event["data"]["object"])


# ── webhook handlers (six; one per architecture handler table row) ─────────────

@_register("checkout.session.completed")
def _on_checkout_completed(obj) -> None:
    user_id = (obj.get("metadata") or {}).get("user_id")
    if not user_id:
        return
    _repo.upsert_from_event_with_plan(
        user_id,
        plan="pro",
        stripe_customer_id=obj["customer"],
        stripe_subscription_id=obj["subscription"],
        stripe_price_id=_PRO_PRICE_ID,
        status="active",
    )


@_register("customer.subscription.updated")
def _on_subscription_updated(obj) -> None:
    user_id = _user_id_for_customer(obj.get("customer"))
    if user_id is None:
        return
    fields: dict = {
        "status": obj["status"],
        "current_period_start": datetime.utcfromtimestamp(obj["current_period_start"]),
        "current_period_end": datetime.utcfromtimestamp(obj["current_period_end"]),
    }
    if obj.get("cancel_at_period_end") and obj.get("cancel_at"):
        fields["canceled_at"] = datetime.utcfromtimestamp(obj["cancel_at"])
    _repo.upsert_from_event(user_id, **fields)


@_register("customer.subscription.deleted")
def _on_subscription_deleted(obj) -> None:
    user_id = _user_id_for_customer(obj.get("customer"))
    if user_id is None:
        return
    _repo.upsert_from_event_with_plan(
        user_id,
        plan="free",
        status="canceled",
        canceled_at=datetime.utcnow(),
    )


@_register("invoice.payment_failed")
def _on_payment_failed(obj) -> None:
    # Option A: user retains Pro access until subscription.deleted.
    # Only status is updated; User.plan is NOT written here.
    sub = _repo.get_by_stripe_subscription_id(obj.get("subscription", ""))
    if sub:
        _repo.upsert_from_event(sub.user_id, status="past_due")


@_register("invoice.paid")
def _on_invoice_paid(obj) -> None:
    sub = _repo.get_by_stripe_subscription_id(obj.get("subscription", ""))
    if sub is None:
        return
    fields: dict = {"status": "active"}
    lines = obj.get("lines", {}).get("data", [])
    if lines:
        period_end = lines[0].get("period", {}).get("end")
        if period_end:
            fields["current_period_end"] = datetime.utcfromtimestamp(period_end)
    _repo.upsert_from_event(sub.user_id, **fields)


@_register("checkout.session.expired")
def _on_checkout_expired(_obj) -> None:
    # Sixth handler — architecture open question resolved as checkout.session.expired.
    # No subscription state to clean; placeholder for future cleanup logic.
    pass


# ── private helpers ───────────────────────────────────────────────────────────

def _user_id_for_customer(customer_id: Optional[str]) -> Optional[str]:
    if not customer_id:
        return None
    sub = _repo.get_by_stripe_customer_id(customer_id)
    return sub.user_id if sub else None
```

**Verify**:
```bash
cd api && python -c "
from modules.billing.service import BillingSignatureError, _HANDLERS
print('handlers registered:', list(_HANDLERS.keys()))
"
```
Expect six keys printed: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`, `invoice.paid`, `checkout.session.expired`.

---

### Step 6: Create auth stub and billing routes

**Action**: Create `modules/auth/decorators.py` (minimal JWT stub) and `modules/billing/routes.py` (three handlers). `routes.py` imports only from `service.py` and `repository.py` — no direct `stripe` import.

**File**: `api/modules/auth/decorators.py` (new)

**Pattern**:
```python
import os
from functools import wraps
from flask import request, jsonify, g


class _CurrentUser:
    __slots__ = ("id", "email", "plan")

    def __init__(self, id: str, email: str, plan: str = "free"):
        self.id = id
        self.email = email
        self.plan = plan


def require_auth(fn):
    """Populate g.current_user or return 401.

    AUTH_BYPASS=true: reads X-User-Id / X-User-Email headers (dev/test only).
    Production: validates a Bearer HS256 JWT via JWT_SECRET env var.
    Replace _verify_jwt with Neon Auth JWT verification in the auth epic.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if os.environ.get("AUTH_BYPASS", "false").lower() == "true":
            g.current_user = _CurrentUser(
                id=request.headers.get("X-User-Id", "test-user"),
                email=request.headers.get("X-User-Email", "test@example.com"),
            )
            return fn(*args, **kwargs)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        token = auth[7:]
        try:
            user_id, email = _verify_jwt(token)
        except Exception:
            return jsonify({"error": "unauthorized"}), 401
        g.current_user = _CurrentUser(id=user_id, email=email)
        return fn(*args, **kwargs)
    return wrapper


def _verify_jwt(token: str):
    """Stub: HS256 decode. Replace with RS256 (Neon Auth) in auth epic."""
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise ValueError("JWT_SECRET not configured")
    from jose import jwt
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return payload["sub"], payload.get("email", "")
```

**File**: `api/modules/billing/routes.py` (new)

**Pattern**:
```python
from flask import Blueprint, request, jsonify, g

from dtos.models import CheckoutSessionResponse, WebhookAckResponse, BillingStatusResponse
from modules.auth.decorators import require_auth
from .service import create_checkout_session, create_portal_session, handle_webhook, BillingSignatureError
from .repository import SubscriptionRepository

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")
_repo = SubscriptionRepository()


@billing_bp.post("/create-checkout-session")
@require_auth
def create_checkout():
    url = create_checkout_session(g.current_user.id, g.current_user.email)
    return jsonify(CheckoutSessionResponse(url=url).model_dump()), 200


@billing_bp.post("/webhook")
def webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        handle_webhook(payload, sig)
    except BillingSignatureError:
        return jsonify({"error": "invalid signature"}), 400
    return jsonify(WebhookAckResponse(received=True).model_dump()), 200


@billing_bp.get("/status")
@require_auth
def billing_status():
    sub = _repo.get_for_user(g.current_user.id)
    manage_url = None
    if sub and sub.stripe_customer_id:
        manage_url = create_portal_session(sub.stripe_customer_id)
    body = BillingStatusResponse(
        plan=sub.plan if sub else "free",
        status=sub.status if sub else "inactive",
        current_period_end=(
            sub.current_period_end.isoformat()
            if sub and sub.current_period_end else None
        ),
        manage_url=manage_url,
    )
    return jsonify(body.model_dump()), 200
```

**Verify**:
```bash
cd api && python -c "
from modules.billing.routes import billing_bp
rules = [str(r) for r in billing_bp.deferred_functions]
print('blueprint created; deferred_functions:', len(billing_bp.deferred_functions))
"
```

---

### Step 7: Wire blueprint, config, and dependencies

**Action**: Register `billing_bp` in `create_app.py`, call `create_db_and_tables()` on app init, extend `config.py` with new env-var reads, and add three packages to `requirements.txt`.

**File**: `api/create_app.py` — two edits

*Edit 1* — add to `ENABLED_MODULES` list (after `spec_gen_bp` entry):
```python
    ('modules.billing.routes',   'billing_bp'),
```

*Edit 2* — add DB initialisation after blueprint registration, before the `workflow_repository` block:
```python
    from db import create_db_and_tables
    with app.app_context():
        create_db_and_tables()
```

**File**: `api/config.py` — append at the bottom:
```python
import os as _os

# Stripe / billing env vars — never appear in code or committed config.
STRIPE_SECRET_KEY: str = _os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET: str = _os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID: str = _os.environ.get("STRIPE_PRO_PRICE_ID", "")
FRONTEND_URL: str = _os.environ.get("FRONTEND_URL", "http://localhost:4201")
DATABASE_URL: str = _os.environ.get("DATABASE_URL", "sqlite:///spec_doc.db")
```

**File**: `api/requirements.txt` — append:
```
stripe>=7.0.0
sqlmodel>=0.0.18
python-jose[cryptography]>=3.3.0
```

**File**: `api/.env` — add (do NOT commit; file is gitignored):
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
FRONTEND_URL=http://localhost:4201
DATABASE_URL=sqlite:///spec_doc.db
```

**Verify**:
```bash
cd api && pip install -r requirements.txt -q
python -c "from create_app import create_app; app = create_app(); print('app wired OK')"
```
Expect `app wired OK`. The `spec_doc.db` file should exist in `api/`.

---

## 5. Tests

### `api/modules/billing/tests/conftest.py`

```python
import pytest
from contextlib import contextmanager
from sqlmodel import create_engine, SQLModel, Session
from unittest.mock import patch


@pytest.fixture(autouse=True)
def billing_db():
    """Isolate all billing tests to an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    from modules.billing.models import User, Subscription  # noqa: F401 — registers metadata
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def _session():
        with Session(engine) as session:
            yield session

    with patch("modules.billing.repository.get_session", _session):
        yield
```

---

### `api/modules/billing/tests/test_repository.py`

```python
import pytest
from modules.billing.repository import SubscriptionRepository


class TestSubscriptionRepository:

    def test_get_for_user_returns_none_when_absent(self):
        repo = SubscriptionRepository()
        result = repo.get_for_user("user-missing")
        assert result is None, "absent user must return None, not raise"

    def test_upsert_creates_new_subscription(self):
        repo = SubscriptionRepository()
        sub = repo.upsert_from_event("user-1", plan="pro", status="active")
        assert sub.user_id == "user-1"
        assert sub.plan == "pro"
        assert sub.status == "active"

    def test_upsert_updates_existing_subscription(self):
        repo = SubscriptionRepository()
        repo.upsert_from_event("user-2", plan="pro", status="active")
        updated = repo.upsert_from_event("user-2", status="past_due")
        assert updated.plan == "pro", "existing plan must be preserved"
        assert updated.status == "past_due", "status must be overwritten"

    def test_upsert_with_plan_writes_user_plan(self):
        repo = SubscriptionRepository()
        repo.get_or_create_user("user-3", "u3@test.com")
        repo.upsert_from_event_with_plan("user-3", plan="pro", status="active")
        user = repo.get_or_create_user("user-3", "u3@test.com")
        assert user.plan == "pro", "User.plan must be written to pro by upsert_with_plan"

    def test_get_by_stripe_customer_id(self):
        repo = SubscriptionRepository()
        repo.upsert_from_event("user-4", stripe_customer_id="cus_test123")
        found = repo.get_by_stripe_customer_id("cus_test123")
        assert found is not None
        assert found.user_id == "user-4"

    def test_get_by_stripe_subscription_id(self):
        repo = SubscriptionRepository()
        repo.upsert_from_event("user-5", stripe_subscription_id="sub_test456")
        found = repo.get_by_stripe_subscription_id("sub_test456")
        assert found is not None
        assert found.user_id == "user-5"
```

---

### `api/modules/billing/tests/test_service.py`

```python
import pytest
from unittest.mock import patch, MagicMock
import modules.billing.service as svc
from modules.billing.service import BillingSignatureError


@pytest.fixture(autouse=True)
def _mock_repo():
    """Replace the singleton repo with a fresh Mock for every test."""
    with patch.object(svc, "_repo") as mock_repo:
        mock_repo.get_for_user.return_value = None
        mock_repo.get_by_stripe_customer_id.return_value = None
        mock_repo.get_by_stripe_subscription_id.return_value = None
        yield mock_repo


class TestWebhookHandlers:

    def test_checkout_completed_upserts_pro_plan(self, _mock_repo):
        obj = {
            "metadata": {"user_id": "user-1"},
            "customer": "cus_abc",
            "subscription": "sub_abc",
        }
        svc._on_checkout_completed(obj)
        _mock_repo.upsert_from_event_with_plan.assert_called_once()
        call_args = _mock_repo.upsert_from_event_with_plan.call_args
        assert call_args[0][0] == "user-1"
        assert call_args[1]["plan"] == "pro"
        assert call_args[1]["status"] == "active"
        assert call_args[1]["stripe_customer_id"] == "cus_abc"

    def test_subscription_deleted_writes_free_plan(self, _mock_repo):
        mock_sub = MagicMock()
        mock_sub.user_id = "user-2"
        _mock_repo.get_by_stripe_customer_id.return_value = mock_sub
        svc._on_subscription_deleted({"customer": "cus_del", "status": "canceled"})
        call_args = _mock_repo.upsert_from_event_with_plan.call_args
        assert call_args[1]["plan"] == "free"
        assert call_args[1]["status"] == "canceled"

    def test_payment_failed_does_not_change_user_plan(self, _mock_repo):
        """Option A: invoice.payment_failed must NOT write User.plan."""
        mock_sub = MagicMock()
        mock_sub.user_id = "user-3"
        _mock_repo.get_by_stripe_subscription_id.return_value = mock_sub
        svc._on_payment_failed({"subscription": "sub_xyz"})
        _mock_repo.upsert_from_event.assert_called_once_with("user-3", status="past_due")
        _mock_repo.upsert_from_event_with_plan.assert_not_called()

    def test_invoice_paid_sets_active_status(self, _mock_repo):
        mock_sub = MagicMock()
        mock_sub.user_id = "user-4"
        _mock_repo.get_by_stripe_subscription_id.return_value = mock_sub
        svc._on_invoice_paid({
            "subscription": "sub_abc",
            "lines": {"data": [{"period": {"end": 1700000000}}]},
        })
        call_kwargs = _mock_repo.upsert_from_event.call_args[1]
        assert call_kwargs["status"] == "active"
        assert "current_period_end" in call_kwargs

    def test_handle_webhook_raises_billing_signature_error_on_bad_sig(self):
        import stripe
        with patch.object(
            stripe.Webhook, "construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad sig", "hdr"),
        ):
            with pytest.raises(BillingSignatureError):
                svc.handle_webhook(b"payload", "bad-sig")

    def test_handle_webhook_ignores_unregistered_event_type(self):
        mock_event = {"type": "some.unknown.event", "data": {"object": {}}}
        with patch.object(svc.stripe.Webhook, "construct_event", return_value=mock_event):
            svc.handle_webhook(b"payload", "valid-sig")   # must not raise
```

---

### `api/modules/billing/tests/test_routes.py`

```python
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _auth_bypass(monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS", "true")


class TestCreateCheckoutSession:

    def test_returns_url_on_success(self, client):
        with patch("modules.billing.service.create_checkout_session",
                   return_value="https://checkout.stripe.com/pay/test"):
            resp = client.post(
                "/api/billing/create-checkout-session",
                headers={"X-User-Id": "u1", "X-User-Email": "u1@test.com"},
            )
        assert resp.status_code == 200
        assert resp.get_json()["url"] == "https://checkout.stripe.com/pay/test"

    def test_returns_401_without_auth(self, client, monkeypatch):
        monkeypatch.delenv("AUTH_BYPASS", raising=False)
        resp = client.post("/api/billing/create-checkout-session")
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "unauthorized"


class TestWebhookEndpoint:

    def test_returns_200_and_received_true_on_valid_event(self, client):
        with patch("modules.billing.routes.handle_webhook", return_value=None):
            resp = client.post(
                "/api/billing/webhook",
                data=b'{"type":"checkout.session.completed","data":{"object":{}}}',
                headers={"Stripe-Signature": "valid_sig", "Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert resp.get_json()["received"] is True

    def test_returns_400_on_invalid_signature(self, client):
        from modules.billing.service import BillingSignatureError
        with patch("modules.billing.routes.handle_webhook",
                   side_effect=BillingSignatureError("bad sig")):
            resp = client.post(
                "/api/billing/webhook",
                data=b"{}",
                headers={"Stripe-Signature": "bad-sig"},
            )
        assert resp.status_code == 400
        assert "invalid signature" in resp.get_json()["error"]


class TestBillingStatus:

    def test_free_user_returns_free_plan_and_null_manage_url(self, client):
        with patch("modules.billing.routes._repo") as mock_repo:
            mock_repo.get_for_user.return_value = None
            resp = client.get(
                "/api/billing/status",
                headers={"X-User-Id": "u1", "X-User-Email": "u1@test.com"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["plan"] == "free"
        assert data["status"] == "inactive"
        assert data["manage_url"] is None

    def test_pro_user_returns_pro_plan_with_manage_url(self, client):
        mock_sub = MagicMock()
        mock_sub.plan = "pro"
        mock_sub.status = "active"
        mock_sub.stripe_customer_id = "cus_pro"
        mock_sub.current_period_end = None
        with (
            patch("modules.billing.routes._repo") as mock_repo,
            patch("modules.billing.routes.create_portal_session",
                  return_value="https://billing.stripe.com/p/session"),
        ):
            mock_repo.get_for_user.return_value = mock_sub
            resp = client.get(
                "/api/billing/status",
                headers={"X-User-Id": "u1", "X-User-Email": "u1@test.com"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["plan"] == "pro"
        assert data["manage_url"] == "https://billing.stripe.com/p/session"

    def test_returns_401_without_auth(self, client, monkeypatch):
        monkeypatch.delenv("AUTH_BYPASS", raising=False)
        resp = client.get("/api/billing/status")
        assert resp.status_code == 401
```

---

### Structural test addition — append to `api/tests/test_structural.py`

```python
def test_stripe_only_imported_in_billing_service():
    """ELA Pattern #1: only modules/billing/service.py may import the stripe SDK."""
    import pathlib
    api_root = pathlib.Path(__file__).parent.parent
    allowed = "modules/billing/service.py"
    violators = []
    for path in sorted(api_root.rglob("*.py")):
        rel = str(path.relative_to(api_root)).replace("\\", "/")
        if "/tests/" in rel or rel.startswith("tests/"):
            continue   # test files may mock stripe; excluded from boundary check
        text = path.read_text(encoding="utf-8")
        if ("import stripe" in text or "from stripe" in text) and not rel.endswith(allowed):
            violators.append(rel)
    assert violators == [], (
        f"stripe SDK imported outside billing service boundary: {violators}. "
        "Move all Stripe calls to modules/billing/service.py."
    )
```

---

## 6. Commit Plan

**Executor instruction**: run each commit as its step completes — not all at the end.

1. `chore(billing): extend openapi.yaml with billing routes and regenerate DTOs` — after Step 1 — files: `openapi.yaml`, `dtos/models.py` (`git add -f dtos/models.py`)
2. `feat(billing): add SQLModel db engine module` — after Step 2 — files: `db.py`
3. `feat(billing): add User and Subscription SQLModel entities` — after Step 3 — files: `modules/billing/__init__.py`, `modules/billing/models.py`
4. `feat(billing): add SubscriptionRepository` — after Step 4 — files: `modules/billing/repository.py`
5. `feat(billing): add billing service with Stripe adapter and six webhook handlers` — after Step 5 — files: `modules/billing/service.py`
6. `feat(billing): add billing Blueprint routes and auth stub` — after Step 6 — files: `modules/billing/routes.py`, `modules/auth/__init__.py`, `modules/auth/decorators.py`
7. `feat(billing): wire billing blueprint into app factory and extend config` — after Step 7 — files: `create_app.py`, `config.py`, `requirements.txt`
8. `test(billing): add repository, service, route, and structural tests` — after tests pass — files: `modules/billing/tests/`, `tests/test_structural.py`

**Deviation logging**: prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → **644** passing (20 new tests: 6 repository + 6 service + 7 routes + 1 structural). Zero pre-existing tests broken. The 1 existing skip remains.

Also run the full check:
```bash
cd api && make lint && make check-dtos
```
Both must exit 0.

---

## 8. Rollback

- **Per-step**: each of the 8 commits is independently revertible — `git revert <sha>`. Steps are ordered so reverting from the top is always safe (later commits depend on earlier ones).
- **Per-branch**: if verification fails catastrophically after Step 7 and the state is unrecoverable by revert, `git reset --hard <sha-before-step-1>` and delete the feature branch. Recover `dtos/models.py` from the Task 1 commit state via `git checkout <task-1-sha> -- api/dtos/models.py`.
- **`spec_doc.db`**: delete it — it's ignored and recreated on next `create_db_and_tables()` call.

---

## 9. Deviations Allowed

- **`dtos/models.py` doesn't contain billing DTOs after `make generate-dtos`**: inspect `openapi.yaml` for schema syntax errors; fix YAML, re-run. Do not hand-edit `dtos/models.py`.
- **`CheckoutSessionResponse` / `BillingStatusResponse` not Pydantic-compatible**: if `model_dump()` is absent (older pydantic v1 style), use `.dict()` in routes.py instead — log deviation in commit.
- **`tests/test_structural.py` doesn't exist** (the explore report said it might be named differently): locate the structural test file with `find api/tests -name "test_struct*"` and append to whatever file exists; if none exists, create `api/tests/test_structural.py` with the snippet above plus the appropriate imports.
- **Step N reveals `client` fixture is project-scoped, not billing-test-accessible**: add a `client` fixture to `modules/billing/tests/conftest.py` that creates the test app directly — do not modify root `conftest.py`.
- **Side-effect required** (e.g., Stripe live-key test, push, schema migration) → STOP, mark `[REQUIRES APPROVAL]`.

---

## 10. Out of Scope

This task delivers the billing module's server-side backend only. Angular wiring — `SubscriptionService`, `pro.guard.ts`, `usage-meter.component.ts`, `usage-limit.interceptor.ts`, and `upgrade.page.ts` — is Task 4 and must not be pre-empted here. The usage metering module (`modules/usage/`) and the `@check_usage_limit` decorator applied to `modules/ai/routes.py` are Task 3, which runs in parallel. An eager executor might notice that `g.current_user.plan` is available after `require_auth` and attempt to add pro-gate logic to AI routes — this belongs entirely in Task 3.

- **Task 3 (usage metering)** — parallel with this task; `UsageCounter` model and `@check_usage_limit` decorator are out of scope here; do not add them to `modules/billing/`
- **Task 4 (Angular billing surface)** — depends on both Task 2 and Task 3; defer all frontend work
- **Full auth epic** — `modules/auth/decorators.py` is a deliberate stub; RS256 (Neon Auth) JWT verification, session refresh, and Apple Sign-In are not in scope here; replace `_verify_jwt` only when the auth epic runs
- **Annual / team / lifetime plans** — ELA #5: one `STRIPE_PRO_PRICE_ID` is the only concrete case; no generalised pricing engine ships here
- **Coupon engine** — applied via Stripe Dashboard; no in-app trigger surface required at this scale
- **`invoice.payment_failed` Option B** (revert to free on first failed payment) — deferred; re-evaluate after first evidence of past-due users consuming material API budget; change would require adding `User.plan` write to `_on_payment_failed` and updating the Option A comment

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale for webhook-only writer, denormalised plan field, and Customer Portal on-demand URL generation
- [Epic](./epic.md) — full task scope and pre-conditions
- [Timeline](./timeline.md) — update status to `in-progress` on start, `done` after verification passes