"""Unit tests for modules.auth.service.

Each test mints a synthetic RS256 JWT signed with a freshly-generated keypair
and monkeypatches modules.auth.service._JWKS_CLIENT with a stub whose
get_signing_key_from_jwt returns the matching public key. No network calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from modules.auth import service
from modules.auth.models import User


def makeKeypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def installJwksStub(monkeypatch, public_key):
    stub = MagicMock()
    stub.get_signing_key_from_jwt.return_value = MagicMock(key=public_key)
    monkeypatch.setattr(service, "_JWKS_CLIENT", stub)


def mintJwt(private_key, claims):
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_verify_jwt_returnsClaimsForValidToken(monkeypatch):
    private_key, public_key = makeKeypair()
    installJwksStub(monkeypatch, public_key)
    token = mintJwt(private_key, {"sub": "u-123", "email": "a@b.co", "aud": "authenticated"})

    claims = service.verify_jwt(token)

    assert claims["sub"] == "u-123"
    assert claims["email"] == "a@b.co"


def test_verify_jwt_raisesOnExpiredToken(monkeypatch):
    private_key, public_key = makeKeypair()
    installJwksStub(monkeypatch, public_key)
    token = mintJwt(
        private_key,
        {"sub": "u-1", "aud": "authenticated", "exp": 1},  # epoch 1970-01-01
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        service.verify_jwt(token)


def test_verify_jwt_raisesOnWrongAudience(monkeypatch):
    private_key, public_key = makeKeypair()
    installJwksStub(monkeypatch, public_key)
    token = mintJwt(private_key, {"sub": "u-1", "aud": "not-authenticated"})

    with pytest.raises(jwt.InvalidAudienceError):
        service.verify_jwt(token)


def test_verify_jwt_raisesOnTamperedSignature(monkeypatch):
    real_private, _ = makeKeypair()
    _, decoy_public = makeKeypair()
    installJwksStub(monkeypatch, decoy_public)
    token = mintJwt(real_private, {"sub": "u-1", "aud": "authenticated"})

    with pytest.raises(jwt.InvalidSignatureError):
        service.verify_jwt(token)


def test_send_magic_link_postsToNeonAuthEndpoint(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        resp = MagicMock()
        resp.json.return_value = {"request_id": "req-abc"}
        resp.raise_for_status = lambda: None
        return resp

    monkeypatch.setattr(service.requests, "post", fake_post)
    monkeypatch.setattr(service, "_NEON_AUTH_API_BASE", "https://auth.example")
    monkeypatch.setattr(service, "_NEON_AUTH_PROJECT_ID", "proj-1")

    result = service.send_magic_link("a@b.co")

    assert result == {"request_id": "req-abc"}
    assert captured["url"] == "https://auth.example/v1/projects/proj-1/auth/magic-link/send"
    assert captured["json"]["email"] == "a@b.co"


def test_verify_magic_link_returnsJwtAndClaims(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        resp = MagicMock()
        resp.json.return_value = {"jwt": "abc.def.ghi", "claims": {"sub": "u-1"}}
        resp.raise_for_status = lambda: None
        return resp

    monkeypatch.setattr(service.requests, "post", fake_post)

    result = service.verify_magic_link("one-time-token")

    assert result["jwt"] == "abc.def.ghi"
    assert result["claims"]["sub"] == "u-1"


def test_get_or_create_user_returnsExistingRow():
    existing = User(id=42, auth_user_id="u-1", email="a@b.co")
    repo = MagicMock()
    repo.get_by_auth_user_id.return_value = existing

    result = service.get_or_create_user_from_claims(
        {"sub": "u-1", "email": "a@b.co"}, repo
    )

    assert result is existing
    repo.create.assert_not_called()


def test_get_or_create_user_createsRowWhenAbsent():
    created = User(id=7, auth_user_id="u-2", email="c@d.co")
    repo = MagicMock()
    repo.get_by_auth_user_id.return_value = None
    repo.create.return_value = created

    result = service.get_or_create_user_from_claims(
        {"sub": "u-2", "email": "c@d.co"}, repo
    )

    assert result is created
    repo.create.assert_called_once_with(auth_user_id="u-2", email="c@d.co")
