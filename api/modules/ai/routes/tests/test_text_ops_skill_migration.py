"""Integration tests for text.py handlers after Phase 2 skill migration.

Verifies that rewrite, iterate, review, lint-braindump handlers:
- Delegate to the skill service (not chain_adapter directly)
- Return the correct response shapes
- Handle FileNotFoundError → 503 (skill unavailable)
- Handle RuntimeError → 502 (skill execution failure)
- Still enforce authentication
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("CHAIN_PROVIDER", "mock")
os.environ["SKIP_AUTH"] = "1"


@pytest.fixture()
def app():
    from create_app import create_app as _create_app
    return _create_app({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


AUTH = {"Authorization": "Bearer skip"}
_REWRITE_REGISTRY = {"name": "rewrite", "version": "1.0.0", "execution_model": "sync",
                     "output_schema": {"type": "object", "required": ["text"]}}
_ITERATE_REGISTRY = {"name": "iterate", "version": "1.0.0", "execution_model": "sync",
                     "output_schema": {"type": "object", "required": ["text"]}}
_REVIEW_REGISTRY = {"name": "review", "version": "1.0.0", "execution_model": "sync",
                    "output_schema": {"type": "object", "required": ["scores", "issues"]}}
_BRAINSTORM_REGISTRY = {"name": "brainstorm", "version": "1.0.0", "execution_model": "async",
                        "output_schema": {"type": "object", "required": ["rewritten_braindump"]}}

_SKILL_SERVICE = "modules.ai.routes.text"


# ---------------------------------------------------------------------------
# rewrite — /api/ai/text/rewrite
# ---------------------------------------------------------------------------

def test_rewrite_calls_skill_service_not_chain_adapter(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_REWRITE_REGISTRY) as mock_reg, \
         patch(f"{_SKILL_SERVICE}.run_skill", return_value={"text": "rewritten"}) as mock_run:
        r = client.post("/api/ai/text/rewrite", headers=AUTH,
                        json={"text": "original text", "instructions": "make it shorter"})
    assert r.status_code == 200
    mock_reg.assert_called_once_with("rewrite")
    mock_run.assert_called_once()
    # Confirm input includes both text and instructions
    call_input = mock_run.call_args[0][1]
    import json as _json
    parsed = _json.loads(call_input)
    assert parsed["text"] == "original text"
    assert parsed["instructions"] == "make it shorter"


def test_rewrite_returns_text_and_latency_ms(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_REWRITE_REGISTRY), \
         patch(f"{_SKILL_SERVICE}.run_skill", return_value={"text": "done"}):
        r = client.post("/api/ai/text/rewrite", headers=AUTH, json={"text": "hello"})
    body = r.get_json()
    assert body["text"] == "done"
    assert "latencyMs" in body
    assert isinstance(body["latencyMs"], int)


def test_rewrite_400_when_text_empty(client):
    r = client.post("/api/ai/text/rewrite", headers=AUTH, json={"text": "  "})
    assert r.status_code == 400


def test_rewrite_503_when_skill_missing(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post("/api/ai/text/rewrite", headers=AUTH, json={"text": "hello"})
    assert r.status_code == 503
    assert "skill unavailable" in r.get_json()["error"]


def test_rewrite_502_on_skill_runtime_error(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_REWRITE_REGISTRY), \
         patch(f"{_SKILL_SERVICE}.run_skill", side_effect=RuntimeError("validation failed")):
        r = client.post("/api/ai/text/rewrite", headers=AUTH, json={"text": "hello"})
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# iterate — /api/ai/text/iterate
# ---------------------------------------------------------------------------

def test_iterate_calls_skill_service(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_ITERATE_REGISTRY), \
         patch(f"{_SKILL_SERVICE}.run_skill", return_value={"text": "updated"}) as mock_run:
        r = client.post("/api/ai/text/iterate", headers=AUTH,
                        json={"document": "# Doc\ncontent", "instruction": "add a summary"})
    assert r.status_code == 200
    import json as _json
    call_input = _json.loads(mock_run.call_args[0][1])
    assert call_input["document"] == "# Doc\ncontent"
    assert call_input["instruction"] == "add a summary"


def test_iterate_422_when_document_empty(client):
    # constr(min_length=1) on the DTO field → Pydantic returns 422 before the handler runs
    r = client.post("/api/ai/text/iterate", headers=AUTH,
                    json={"document": "", "instruction": "do something"})
    assert r.status_code == 422


def test_iterate_503_when_skill_missing(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post("/api/ai/text/iterate", headers=AUTH,
                        json={"document": "content", "instruction": "update it"})
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# review — /api/ai/text/review
# ---------------------------------------------------------------------------

def test_review_calls_skill_service(client):
    skill_result = {"scores": {"clarity": 4, "completeness": 3, "actionability": 5,
                               "consistency": 4, "specificity": 3, "feasibility": 5},
                    "issues": ["Missing success criteria"]}
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_REVIEW_REGISTRY), \
         patch(f"{_SKILL_SERVICE}.run_skill", return_value=skill_result) as mock_run:
        r = client.post("/api/ai/text/review", headers=AUTH,
                        json={"documents": {"epic.md": "# Epic\ncontent"}})
    assert r.status_code == 200
    import json as _json
    call_input = _json.loads(mock_run.call_args[0][1])
    assert "documents" in call_input


def test_review_returns_scores_and_issues(client):
    skill_result = {"scores": {"clarity": 5, "completeness": 5, "actionability": 5,
                               "consistency": 5, "specificity": 5, "feasibility": 5},
                    "issues": []}
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_REVIEW_REGISTRY), \
         patch(f"{_SKILL_SERVICE}.run_skill", return_value=skill_result):
        r = client.post("/api/ai/text/review", headers=AUTH,
                        json={"documents": {"epic.md": "content"}})
    body = r.get_json()
    assert "scores" in body
    assert "issues" in body


def test_review_503_when_skill_missing(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post("/api/ai/text/review", headers=AUTH,
                        json={"documents": {"epic.md": "content"}})
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# lint-braindump → brainstorm — /api/ai/text/lint-braindump
# ---------------------------------------------------------------------------

def test_lint_braindump_calls_brainstorm_skill(client):
    brainstorm_result = {
        "questions": [{"area": "auth", "question": "Single user?"}],
        "recommendations": [],
        "rewritten_braindump": "# Sharp braindump\n\nReady for spec-pipeline.",
        "suggested_action": "run spec-pipeline",
    }
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_BRAINSTORM_REGISTRY) as mock_reg, \
         patch(f"{_SKILL_SERVICE}.run_skill", return_value=brainstorm_result):
        r = client.post("/api/ai/text/lint-braindump", headers=AUTH,
                        json={"braindump": "rough idea here"})
    assert r.status_code == 200
    mock_reg.assert_called_once_with("brainstorm")
    body = r.get_json()
    assert "rewritten_braindump" in body
    assert "questions" in body


def test_lint_braindump_422_when_braindump_empty(client):
    # constr(min_length=1) on the DTO field → Pydantic returns 422 before the handler runs
    r = client.post("/api/ai/text/lint-braindump", headers=AUTH, json={"braindump": ""})
    assert r.status_code == 422


def test_lint_braindump_503_when_skill_missing(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", side_effect=FileNotFoundError):
        r = client.post("/api/ai/text/lint-braindump", headers=AUTH,
                        json={"braindump": "some ideas"})
    assert r.status_code == 503


def test_lint_braindump_502_on_skill_runtime_error(client):
    with patch(f"{_SKILL_SERVICE}.load_skill_registry", return_value=_BRAINSTORM_REGISTRY), \
         patch(f"{_SKILL_SERVICE}.run_skill", side_effect=RuntimeError("timeout")):
        r = client.post("/api/ai/text/lint-braindump", headers=AUTH,
                        json={"braindump": "some ideas"})
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# No AI strings in text.py — invariant test
# ---------------------------------------------------------------------------

def test_no_ai_instruction_strings_in_text_routes():
    """The core Phase 2 invariant: zero natural-language AI instructions in Python."""
    from pathlib import Path
    source = (Path(__file__).parent.parent.parent / "routes" / "text.py").read_text()
    ai_markers = ["You are a", "you are a", "Return ONLY", "Return only valid JSON"]
    for marker in ai_markers:
        assert marker not in source, (
            f"AI instruction string found in text.py: {marker!r} — "
            "all instructions must live in plugin/skills/*/SKILL.md"
        )
