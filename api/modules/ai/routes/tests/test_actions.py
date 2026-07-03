"""Integration tests for /api/actions blueprint (the inline text-verb surface).

After the write-service migration ("no backend per product" PoC):
- ALL EIGHT verbs (expand, compress, clarify, simplify, tldr, bullets, rewrite,
  brainstorm) forward to the shared oll-am write-service via ``write_client`` —
  these tests mock the ``write_client`` boundary (run_verb / rewrite / brainstorm),
  NOT any local skill runner (there is none for these verbs anymore).
- Response body is always ``{"text", "latencyMs"}`` (the frontend contract).
- rewrite: style→instructions mapping; invalid style → 400.
- brainstorm: optional question/context forward through.
- A ``WriteServiceError`` relays the upstream status when known, else 502.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("CHAIN_PROVIDER", "mock")
os.environ["SKIP_AUTH"] = "1"

_MODULE = "modules.ai.routes.actions"
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
# Single-input verbs — served by write-service (write_client.run_verb)
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
# brainstorm — now ALSO served by write-service (write_client.brainstorm)
# ---------------------------------------------------------------------------

def test_brainstorm_happy_path(client):
    with patch(f"{_MODULE}.write_client.brainstorm", return_value=_WRITE_RESULT) as m:
        r = client.post("/api/brainstorm", headers=AUTH,
                        json={"text": "hello", "question": "what next?", "context": "ctx"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["text"] == "ok"
    assert "latencyMs" in body
    # text + question + context + forwarded Bearer reach write-service.
    called_text, called_question, called_context, called_token = m.call_args[0]
    assert called_text == "hello"
    assert called_question == "what next?"
    assert called_context == "ctx"
    assert called_token == "skip"


def test_brainstorm_optional_fields_default_to_empty(client):
    with patch(f"{_MODULE}.write_client.brainstorm", return_value=_WRITE_RESULT) as m:
        r = client.post("/api/brainstorm", headers=AUTH, json={"text": "hello"})
    assert r.status_code == 200
    _text, question, context, _token = m.call_args[0]
    assert question == ""
    assert context == ""


def test_brainstorm_missing_text_returns_400(client):
    with patch(f"{_MODULE}.write_client.brainstorm", return_value=_WRITE_RESULT):
        r = client.post("/api/brainstorm", headers=AUTH, json={})
    assert r.status_code == 400


def test_brainstorm_relays_upstream_402(client):
    from modules.ai.write_client import WriteServiceError
    envelope = {"code": "PLAN_LIMIT_REACHED", "message": "upgrade", "request_id": "r3"}
    exc = WriteServiceError("over limit", status=402, body=envelope)
    with patch(f"{_MODULE}.write_client.brainstorm", side_effect=exc):
        r = client.post("/api/brainstorm", headers=AUTH, json={"text": "x"})
    assert r.status_code == 402
    assert r.get_json() == envelope


def test_brainstorm_transport_failure_returns_502(client):
    from modules.ai.write_client import WriteServiceError
    with patch(f"{_MODULE}.write_client.brainstorm", side_effect=WriteServiceError("down")):
        r = client.post("/api/brainstorm", headers=AUTH, json={"text": "x"})
    assert r.status_code == 502
    assert "error" in r.get_json()
