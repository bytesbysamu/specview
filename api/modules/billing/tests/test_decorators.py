"""Auth decorator stub coverage."""
from flask import Flask, g, jsonify

# Alias to keep the imported decorator out of pytest's '*_*' collection glob.
from modules.billing import decorators as bd
from modules.billing.decorators import _CurrentUser

requireAuth = bd.require_auth


def buildApp():
    app = Flask(__name__)
    app.testing = True

    @app.get("/who")
    @requireAuth
    def who():
        return jsonify(
            {"auth_user_id": g.current_user.auth_user_id, "email": g.current_user.email}
        )

    return app


def test_require_auth_bypass_reads_headers(monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS", "true")
    app = buildApp()
    client = app.test_client()
    resp = client.get(
        "/who", headers={"X-User-Id": "abc", "X-User-Email": "a@b.com"}
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"auth_user_id": "abc", "email": "a@b.com"}


def test_require_auth_returns_401_without_bypass_or_bearer(monkeypatch):
    monkeypatch.delenv("AUTH_BYPASS", raising=False)
    app = buildApp()
    resp = app.test_client().get("/who")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "unauthorized"}


def test_require_auth_returns_401_when_jwt_verification_raises(monkeypatch):
    monkeypatch.delenv("AUTH_BYPASS", raising=False)
    app = buildApp()
    resp = app.test_client().get(
        "/who", headers={"Authorization": "Bearer not-a-real-token"}
    )
    # _verify_jwt is a stub that raises NotImplementedError; the decorator
    # must convert any exception into 401.
    assert resp.status_code == 401


def test_current_user_slots_only_carries_expected_attrs():
    user = _CurrentUser(auth_user_id="x", email="x@y.com")
    assert user.auth_user_id == "x"
    assert user.email == "x@y.com"
    assert _CurrentUser.__slots__ == ("auth_user_id", "email")
