"""Integration tests for /api/actions blueprint (Phase 3 thin routes).

Covers:
- Happy-path 200 for every route (mock run_skill → {"text": "ok"})
- Response body always has "text" and "latencyMs" keys
- rewrite with invalid style → 400
- missing text → 400
- FileNotFoundError → 503
- RuntimeError → 500
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("CHAIN_PROVIDER", "mock")
os.environ["SKIP_AUTH"] = "1"

_MODULE = "modules.ai.routes.actions"
_REGISTRY = {"name": "expand", "version": "1.0.0", "execution_model": "sync",
             "output_schema": {"type": "object", "required": ["text"]}}
AUTH = {"Authorization": "Bearer skip"}


@pytest.fixture()
def app():
    from create_app import create_app as _create_app
    return _create_app({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_mock_skill(result=None):
    """Patch context manager that stubs both load_skill_registry and run_skill."""
    from unittest.mock import patch as _patch
    if result is None:
        result = {"text": "ok"}
    return (
        _patch(f"{_MODULE}.load_skill_registry", return_value=_REGISTRY),
        _patch(f"{_MODULE}.run_skill", return_value=result),
    )


# ---------------------------------------------------------------------------
# Uniform-verb handlers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("verb", ["expand", "compress", "clarify", "simplify", "tldr", "bullets"])
def test_uniform_verb_happy_path(client, verb):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post(f"/api/{verb}", headers=AUTH, json={"text": "hello world"})
    assert r.status_code == 200
    body = r.get_json()
    assert "text" in body
    assert "latencyMs" in body


@pytest.mark.parametrize("verb", ["expand", "compress", "clarify", "simplify", "tldr", "bullets"])
def test_uniform_verb_missing_text_returns_400(client, verb):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post(f"/api/{verb}", headers=AUTH, json={})
    assert r.status_code == 400


@pytest.mark.parametrize("verb", ["expand", "compress", "clarify", "simplify", "tldr", "bullets"])
def test_uniform_verb_503_on_file_not_found(client, verb):
    with patch(f"{_MODULE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post(f"/api/{verb}", headers=AUTH, json={"text": "x"})
    assert r.status_code == 503


@pytest.mark.parametrize("verb", ["expand", "compress", "clarify", "simplify", "tldr", "bullets"])
def test_uniform_verb_500_on_runtime_error(client, verb):
    with patch(f"{_MODULE}.load_skill_registry", return_value=_REGISTRY), \
         patch(f"{_MODULE}.run_skill", side_effect=RuntimeError("ai down")):
        r = client.post(f"/api/{verb}", headers=AUTH, json={"text": "x"})
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# brainstorm
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# rewrite
# ---------------------------------------------------------------------------

def test_rewrite_happy_path(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Concise"})
    assert r.status_code == 200
    body = r.get_json()
    assert "text" in body
    assert "latencyMs" in body


@pytest.mark.parametrize("style", ["Concise", "Technical", "Executive", "Narrative", "Punchy"])
def test_rewrite_all_valid_styles(client, style):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": style})
    assert r.status_code == 200


def test_rewrite_invalid_style_returns_400(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Invalid"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid style"


def test_rewrite_missing_text_returns_400(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/rewrite", headers=AUTH, json={"style": "Concise"})
    assert r.status_code == 400


def test_rewrite_missing_style_returns_400(client):
    reg_patch, run_patch = _make_mock_skill()
    with reg_patch, run_patch:
        r = client.post("/api/rewrite", headers=AUTH, json={"text": "hello"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid style"


def test_rewrite_503_on_file_not_found(client):
    with patch(f"{_MODULE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Concise"})
    assert r.status_code == 503


def test_rewrite_500_on_runtime_error(client):
    with patch(f"{_MODULE}.load_skill_registry", return_value=_REGISTRY), \
         patch(f"{_MODULE}.run_skill", side_effect=RuntimeError("ai down")):
        r = client.post("/api/rewrite", headers=AUTH,
                        json={"text": "hello", "style": "Concise"})
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Rail 1: timeout ceiling
# ---------------------------------------------------------------------------

class TestActionTimeout:
    """Rail 1: 120s ceiling — timeout returns envelope + 500."""

    @pytest.mark.parametrize("route", [
        "/api/brainstorm", "/api/expand", "/api/compress", "/api/clarify",
        "/api/simplify", "/api/tldr", "/api/bullets",
    ])
    def test_timeout_returns_500_envelope(self, client, monkeypatch, route):
        def _timeout(*a, **kw):
            raise RuntimeError("skill timed out after 120s")
        monkeypatch.setattr(f"{_MODULE}.load_skill_registry", lambda *a: _REGISTRY)
        monkeypatch.setattr(f"{_MODULE}._run_with_timeout", _timeout)
        resp = client.post(route, json={"text": "hello"}, headers=AUTH)
        assert resp.status_code == 500
        assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# Rail 2: missing 'text' key in skill output
# ---------------------------------------------------------------------------

class TestActionMalformedOutput:
    """Rail 2: missing 'text' key returns envelope + 500."""

    def test_missing_text_key_returns_500_envelope(self, client, monkeypatch):
        monkeypatch.setattr(f"{_MODULE}.load_skill_registry", lambda *a: _REGISTRY)
        monkeypatch.setattr(
            f"{_MODULE}._run_with_timeout",
            lambda *a, **kw: {"wrong_key": "value"},
        )
        resp = client.post("/api/brainstorm", json={"text": "hello"}, headers=AUTH)
        assert resp.status_code == 500
        assert "error" in resp.get_json()
