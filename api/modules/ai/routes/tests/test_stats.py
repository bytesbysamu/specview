"""Route-level tests for GET /api/ai/stats.

The stats_bp blueprint is NOT yet registered in create_app.ENABLED_MODULES —
that registration is the SaaS Anthropic SDK Provider wrap-up commit. Until
then we exercise the route through a self-contained Flask app so the
contract for stats_bp itself is tested independently of the wrap-up.

A follow-up wrap-up test using create_app() and the registered blueprint
will pin the integration once ENABLED_MODULES is extended.
"""
from __future__ import annotations

import pytest
from flask import Flask

from modules.ai.routes.stats import stats_bp
from modules.runtime.chain import adapter
from modules.runtime.chain.types import ChainResult


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    app = Flask(__name__)
    app.register_blueprint(stats_bp)
    with app.test_client() as c:
        yield c


def resetUsage() -> None:
    with adapter._USAGE_LOCK:
        adapter._USAGE["calls"] = 0
        adapter._USAGE["input_tokens"] = 0
        adapter._USAGE["output_tokens"] = 0
        adapter._USAGE["by_model"].clear()


def statsEndpoint_returnsZeroSnapshotAtStart(client):
    resetUsage()
    resp = client.get("/api/ai/stats")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["calls"] == 0
    assert body["input_tokens"] == 0
    assert body["output_tokens"] == 0
    assert body["cost_usd"] == 0.0
    assert body["provider"] in {"mock", "cli", "claude", "anthropic"}


def statsEndpoint_reflectsRecordedUsage(client):
    resetUsage()
    adapter._record_usage(
        "claude-sonnet-4-5",
        ChainResult(text="x", latency_ms=1, tokens_in=1000, tokens_out=500),
    )
    resp = client.get("/api/ai/stats")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["calls"] == 1
    assert body["input_tokens"] == 1000
    assert body["output_tokens"] == 500
    # 1000/1e6 * 3 + 500/1e6 * 15 = 0.003 + 0.0075 = 0.0105
    assert body["cost_usd"] == 0.0105


def statsEndpoint_payloadValidatesAgainstDto(client):
    """If the openapi schema drifts from the route output, this fails loud."""
    resetUsage()
    resp = client.get("/api/ai/stats")
    assert resp.status_code == 200
    from dtos.models import AiStatsResponse

    AiStatsResponse(**resp.get_json())  # raises ValidationError on drift
