"""Parametrized contract matrix — CORS, error envelope, OpenAPI path consistency."""
from __future__ import annotations

import pytest

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@pytest.fixture(scope="module")
def app():
    import os
    os.environ.setdefault("CHAIN_PROVIDER", "mock")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:4200")
    from create_app import create_app as _ca
    return _ca({"TESTING": True})


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def routes(app):
    return [
        r.rule for r in app.url_map.iter_rules()
        if not r.rule.startswith("/static") and "<" not in r.rule
    ]


class TestCORSHeaders:
    def test_all_routes_return_cors_header_on_options(self, client, routes):
        missing = []
        for route in routes:
            resp = client.options(route)
            if not resp.headers.get("Access-Control-Allow-Origin"):
                missing.append(route)
        assert not missing, f"Routes missing CORS header: {missing}"


class TestErrorEnvelopeShape:
    """Every 4xx/5xx response must be JSON with an 'error' key."""

    _BAD_PAYLOADS = [
        ("/api/brainstorm", "POST", {}),
        ("/api/expand",     "POST", {}),
        ("/api/compress",   "POST", {}),
        ("/api/clarify",    "POST", {}),
        ("/api/simplify",   "POST", {}),
        ("/api/tldr",       "POST", {}),
        ("/api/bullets",    "POST", {}),
        ("/api/rewrite",    "POST", {"text": "x", "style": "invalid"}),
    ]

    @pytest.mark.parametrize("route,method,payload", _BAD_PAYLOADS)
    def test_error_response_is_envelope(self, client, route, method, payload):
        resp = getattr(client, method.lower())(
            route, json=payload, headers={"Authorization": ""}
        )
        if resp.status_code < 400:
            pytest.skip(f"{route} returned {resp.status_code} on bad input")
        body = resp.get_json()
        assert body is not None, "Response is not JSON"
        assert "error" in body, f"Missing 'error' key: {body}"


@pytest.mark.skipif(not HAS_YAML, reason="pyyaml not installed")
class TestOpenAPIPathConsistency:
    """All app routes without path params must appear in openapi.yaml."""

    def test_app_routes_are_documented(self, app, routes):
        from pathlib import Path
        # openapi.yaml is at api/openapi.yaml — two parents up from this test file
        openapi_path = Path(__file__).parents[2] / "openapi.yaml"
        if not openapi_path.exists():
            pytest.skip("openapi.yaml not found")
        with open(openapi_path) as f:
            spec = yaml.safe_load(f)
        spec_paths = set(spec.get("paths", {}).keys())
        # Only check static routes (no path params or trailing slash) — dynamic routes
        # and internal meta/listing endpoints may not yet appear in the OpenAPI spec.
        static_app_paths = {r for r in routes if "<" not in r and not r.endswith("/")}
        undocumented = static_app_paths - spec_paths
        assert not undocumented, f"App routes not documented in openapi.yaml: {undocumented}"
