"""Integration tests for /api/actions blueprint (the inline text-verb surface).

After the write-service migration ("no backend per product" PoC):
- The SEVEN mappable verbs (expand, compress, clarify, simplify, tldr, bullets,
  rewrite) forward to the shared oll-am write-service via ``write_client`` — these
  tests mock ``write_client.run_verb`` / ``write_client.rewrite`` (the seam), NOT
  the local skill runner.
- ``brainstorm`` is the ONE remaining LOCAL verb — still mocked via ``run_skill``.
- Response body is always ``{"text", "latencyMs"}`` (the frontend contract).
- rewrite: style→instructions mapping; invalid style → 400.
- A ``WriteServiceError`` relays the upstream status when known, else 502.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("CHAIN_PROVIDER", "mock")
os.environ["SKIP_AUTH"] = "1"

_MODULE = "modules.ai.routes.actions"
_REGISTRY = {"name": "brainstorm", "version": "1.0.0", "execution_model": "sync",
             "output_schema": {"type": "object", "required": ["text"]}}
AUTH = {"Authorization": "Bearer skip"}

# What write_client returns to the route: narrowed {text, provider, model}.
_WRITE_RESULT = {"text": "ok", "provider": "groq", "model": "llama-3.3-70b-versatile"}

_MAPPED_VERBS = ["expand", "compress", "clarify", "simplify", "tldr", "bullets"]


@pytest.fixture()
def app():
    from create_app import create_app as _create_app
    return _create_app({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Single-input verbs — now served by write-service (write_client.run_verb)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("verb", _MAPPED_VERBS)
def test_uniform_verb_happy_path(client, verb):
    with patch(f"{_MODULE}.write_client.run_verb", return_value=_WRITE_RESULT) as m:
        r = client.post(f"/api/{verb}", headers=AUTH, json={"text": "hello world"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["text"] == "ok"
    assert "latencyMs" in body
    # The verb + text + forwarded Bearer reach write-service.
    called_verb, called_text, called_token = m.call_args[0]
    assert called_verb == verb
    assert called_text == "hello world"
    assert called_token == "skip"


@pytest.mark.parametrize("verb", _MAPPED_VERBS)
def test_uniform_verb_missing_text_returns_400(client, verb):
    with patch(f"{_MODULE}.write_client.run_verb", return_value=_WRITE_RESULT):
        r = client.post(f"/api/{verb}", headers=AUTH, json={})
    assert r.status_code == 400


@pytest.mark.parametrize("verb", _MAPPED_VERBS)
def test_uniform_verb_relays_upstream_402(client, verb):
    from modules.ai.write_client import WriteServiceError
    envelope = {"code": "PLAN_LIMIT_REACHED", "message": "upgrade", "request_id": "r1"}
    exc = WriteServiceError("over limit", status=402, body=envelope)
    with patch(f"{_MODULE}.write_client.run_verb", side_effect=exc):
        r = client.post(f"/api/{verb}", headers=AUTH, json={"text": "x"})
    assert r.status_code == 402
    assert r.get_json() == envelope


@pytest.mark.parametrize("verb", _MAPPED_VERBS)
def test_uniform_verb_transport_failure_returns_502(client, verb):
    from modules.ai.write_client import WriteServiceError
    with patch(f"{_MODULE}.write_client.run_verb", side_effect=WriteServiceError("down")):
        r = client.post(f"/api/{verb}", headers=AUTH, json={"text": "x"})
    assert r.status_code == 502
    assert "error" in r.get_json()


# ---------------------------------------------------------------------------
# rewrite — served by write-service; style → instructions mapping
# ---------------------------------------------------------------------------

def test_rewrite_happy_path(client):
    with patch(f"{_MODULE}.write_client.rewrite", return_value=_WRITE_RESULT):
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Concise"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["text"] == "ok"
    assert "latencyMs" in body


@pytest.mark.parametrize("style", ["Concise", "Technical", "Executive", "Narrative", "Punchy"])
def test_rewrite_all_valid_styles_map_to_instructions(client, style):
    with patch(f"{_MODULE}.write_client.rewrite", return_value=_WRITE_RESULT) as m:
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": style})
    assert r.status_code == 200
    # style is translated to a non-empty instructions string forwarded to write-service.
    _text, instructions, _token = m.call_args[0]
    assert isinstance(instructions, str) and instructions
    assert style.lower() in instructions.lower()


def test_rewrite_forwards_bearer(client):
    with patch(f"{_MODULE}.write_client.rewrite", return_value=_WRITE_RESULT) as m:
        client.post("/api/rewrite", headers=AUTH, json={"text": "hi", "style": "Punchy"})
    assert m.call_args[0][2] == "skip"


def test_rewrite_invalid_style_returns_400(client):
    r = client.post("/api/rewrite", headers=AUTH,
                    json={"text": "hello", "style": "Invalid"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid style"


def test_rewrite_missing_text_returns_400(client):
    r = client.post("/api/rewrite", headers=AUTH, json={"style": "Concise"})
    assert r.status_code == 400


def test_rewrite_missing_style_returns_400(client):
    r = client.post("/api/rewrite", headers=AUTH, json={"text": "hello"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid style"


def test_rewrite_relays_upstream_status(client):
    from modules.ai.write_client import WriteServiceError
    envelope = {"code": "UNAUTHORIZED", "message": "bad token", "request_id": "r2"}
    with patch(f"{_MODULE}.write_client.rewrite",
               side_effect=WriteServiceError("401", status=401, body=envelope)):
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Concise"})
    assert r.status_code == 401
    assert r.get_json() == envelope


def test_rewrite_transport_failure_returns_502(client):
    from modules.ai.write_client import WriteServiceError
    with patch(f"{_MODULE}.write_client.rewrite", side_effect=WriteServiceError("down")):
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Concise"})
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# brainstorm — the ONE remaining LOCAL verb (still runs the local skill)
# ---------------------------------------------------------------------------

def _make_mock_skill(result=None):
    """Patch context managers that stub the LOCAL skill runner for brainstorm."""
    from unittest.mock import patch as _patch
    if result is None:
        result = {"text": "ok"}
    return (
        _patch(f"{_MODULE}.load_skill_registry", return_value=_REGISTRY),
        _patch(f"{_MODULE}.run_skill", return_value=result),
    )


def test_brainstorm_happy_path(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/brainstorm", headers=AUTH,
                        json={"text": "hello", "question": "what next?", "context": "ctx"})
    assert r.status_code == 200
    body = r.get_json()
    assert "text" in body
    assert "latencyMs" in body


def test_brainstorm_optional_fields_default_to_empty(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch as mock_run:
        r = client.post("/api/brainstorm", headers=AUTH, json={"text": "hello"})
    assert r.status_code == 200
    import json as _json
    call_input = mock_run.call_args[0][1]
    parsed = _json.loads(call_input)
    assert parsed["question"] == ""
    assert parsed["context"] == ""


def test_brainstorm_missing_text_returns_400(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/brainstorm", headers=AUTH, json={})
    assert r.status_code == 400


def test_brainstorm_503_when_skill_dir_missing(client):
    with patch(f"{_MODULE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post("/api/brainstorm", headers=AUTH, json={"text": "x"})
    assert r.status_code == 503


class TestBrainstormLocalFailureModes:
    """brainstorm still owns the LOCAL failure modes (timeout, malformed output)."""

    def test_timeout_returns_500_envelope(self, client, monkeypatch):
        def _timeout(*a, **kw):
            raise RuntimeError("skill timed out after 300s")
        monkeypatch.setattr(f"{_MODULE}.load_skill_registry", lambda *a: _REGISTRY)
        monkeypatch.setattr(f"{_MODULE}._run_with_timeout", _timeout)
        resp = client.post("/api/brainstorm", json={"text": "hello"}, headers=AUTH)
        assert resp.status_code == 500
        assert "error" in resp.get_json()

    def test_missing_text_key_returns_500_envelope(self, client, monkeypatch):
        monkeypatch.setattr(f"{_MODULE}.load_skill_registry", lambda *a: _REGISTRY)
        monkeypatch.setattr(
            f"{_MODULE}._run_with_timeout",
            lambda *a, **kw: {"wrong_key": "value"},
        )
        resp = client.post("/api/brainstorm", json={"text": "hello"}, headers=AUTH)
        assert resp.status_code == 500
        assert "error" in resp.get_json()
