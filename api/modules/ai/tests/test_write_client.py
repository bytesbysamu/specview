"""Tests for the write-service boundary (write_client) — the text-ops seam.

The contract under test (from services/write/openapi.yaml):
  POST /api/write/<verb>   (Authorization: Bearer) → {"text","provider","model"}
  POST /api/write/rewrite  (Authorization: Bearer) → {"text","provider","model"}

``run_verb`` / ``rewrite`` forward the Bearer, narrow the body, and on any non-2xx
raise WriteServiceError carrying the upstream status + envelope so the action route
can relay write-service's 401/402/429 verbatim. A transport failure raises with no
status → the route maps it to a 502.
"""
from __future__ import annotations

import pytest
import requests

from modules.ai import write_client


class _Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code}")
            err.response = self
            raise err

    def json(self):
        return self._body


@pytest.mark.parametrize("verb", ["expand", "compress", "clarify", "simplify", "tldr", "bullets"])
def test_run_verb_posts_text_and_forwards_bearer(monkeypatch, verb):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _Resp(200, {"text": "  result  ", "provider": "groq", "model": "llama-3.3-70b"})

    monkeypatch.setattr(requests, "post", fake_post)
    out = write_client.run_verb(verb, "some text", "core-jwt-123")

    assert out == {"text": "result", "provider": "groq", "model": "llama-3.3-70b"}
    assert captured["url"].endswith(f"/api/write/{verb}")
    assert captured["json"] == {"text": "some text"}
    assert captured["headers"]["Authorization"] == "Bearer core-jwt-123"


def test_run_verb_unknown_verb_raises():
    with pytest.raises(write_client.WriteServiceError):
        write_client.run_verb("brainstorm", "x", "jwt")


def test_rewrite_forwards_instructions_and_bearer(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _Resp(200, {"text": "clearer", "provider": "groq", "model": "m"})

    monkeypatch.setattr(requests, "post", fake_post)
    out = write_client.rewrite("draft", "rewrite concisely", "core-jwt-9")

    assert out == {"text": "clearer", "provider": "groq", "model": "m"}
    assert captured["url"].endswith("/api/write/rewrite")
    assert captured["json"]["text"] == "draft"
    assert captured["json"]["instructions"] == "rewrite concisely"
    assert captured["headers"]["Authorization"] == "Bearer core-jwt-9"


def test_rewrite_omits_instructions_when_absent(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _Resp(200, {"text": "x", "provider": "g", "model": "m"})

    monkeypatch.setattr(requests, "post", fake_post)
    write_client.rewrite("draft", None, "jwt")
    assert "instructions" not in captured["json"]
    assert captured["json"]["text"] == "draft"


def test_relays_upstream_status_and_body(monkeypatch):
    envelope = {"code": "PLAN_LIMIT_REACHED", "message": "upgrade", "request_id": "r1"}
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(402, envelope))
    with pytest.raises(write_client.WriteServiceError) as ei:
        write_client.run_verb("expand", "draft", "jwt")
    assert ei.value.upstream_status == 402
    assert ei.value.upstream_body == envelope


def test_transport_failure_has_no_status(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(write_client.WriteServiceError) as ei:
        write_client.run_verb("compress", "draft", "jwt")
    assert ei.value.upstream_status is None
    assert ei.value.upstream_body is None


def test_empty_text_response_raises(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(200, {"text": "   ", "provider": "g", "model": "m"}))
    with pytest.raises(write_client.WriteServiceError):
        write_client.run_verb("tldr", "draft", "jwt")
