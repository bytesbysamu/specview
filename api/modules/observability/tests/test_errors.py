"""Integration tests for ``modules.observability.errors``.

Each test wires ``register_error_handlers`` onto a fresh Flask app so the
shared ``create_app`` fixture is irrelevant. ``PROPAGATE_EXCEPTIONS`` is
disabled because Flask's test client otherwise re-raises exceptions instead
of routing them through registered handlers when ``TESTING`` is True.

The asserted JSON shape mirrors the existing inline handlers in
``create_app.py`` so the wrap-up commit can swap implementations safely.

Note: the production callable is imported through the module namespace so
pytest's permissive ``python_functions = ["test_*", "*_*"]`` collector does
not treat it as a test case.
"""

import pytest
from flask import Flask
from pydantic import BaseModel
from werkzeug.exceptions import Forbidden, NotFound

from modules.observability import errors as errors_mod


@pytest.fixture()
def app():
    a = Flask(__name__)
    a.config["TESTING"] = True
    a.config["PROPAGATE_EXCEPTIONS"] = False
    errors_mod.register_error_handlers(a)
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


class TestHTTPExceptionHandler:
    def test_404_returns_status_404(self, app, client):
        @app.route("/trigger-404")
        def _h():
            raise NotFound("resource missing")

        resp = client.get("/trigger-404")
        assert resp.status_code == 404

    def test_404_body_matches_envelope(self, app, client):
        @app.route("/trigger-404-body")
        def _h():
            raise NotFound("resource missing")

        resp = client.get("/trigger-404-body")
        data = resp.get_json()
        assert data == {"error": "resource missing", "status": 404}

    def test_403_returns_status_403(self, app, client):
        @app.route("/trigger-403")
        def _h():
            raise Forbidden("nope")

        resp = client.get("/trigger-403")
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == 403
        assert data["error"] == "nope"

    def test_response_is_json_content_type(self, app, client):
        @app.route("/trigger-ct")
        def _h():
            raise NotFound("x")

        resp = client.get("/trigger-ct")
        assert resp.content_type.startswith("application/json")


class TestValidationErrorHandler:
    def test_returns_422(self, app, client):
        class M(BaseModel):
            age: int

        @app.route("/trigger-validation")
        def _h():
            M(age="not-a-number")
            return "unreachable"

        resp = client.get("/trigger-validation")
        assert resp.status_code == 422

    def test_envelope_keys(self, app, client):
        class M(BaseModel):
            age: int

        @app.route("/trigger-validation-keys")
        def _h():
            M(age="bad")
            return "unreachable"

        resp = client.get("/trigger-validation-keys")
        data = resp.get_json()
        assert data["error"] == "validation_failed"
        assert data["status"] == 422
        assert isinstance(data["details"], list)
        assert len(data["details"]) >= 1

    def test_details_carry_field_location(self, app, client):
        class M(BaseModel):
            count: int

        @app.route("/trigger-validation-loc")
        def _h():
            M(count="not-an-int")
            return "unreachable"

        resp = client.get("/trigger-validation-loc")
        data = resp.get_json()
        first = data["details"][0]
        # Pydantic v2 includes 'loc'; permissive for v1/v2 drift.
        assert "loc" in first or "input" in first


class TestUnhandledExceptionHandler:
    def test_returns_500(self, app, client):
        @app.route("/trigger-500")
        def _h():
            raise RuntimeError("boom")

        resp = client.get("/trigger-500")
        assert resp.status_code == 500

    def test_envelope_matches_existing_inline_handler(self, app, client):
        @app.route("/trigger-500-body")
        def _h():
            raise RuntimeError("boom")

        resp = client.get("/trigger-500-body")
        data = resp.get_json()
        assert data == {"error": "Internal server error", "status": 500}

    def test_logs_stack_trace(self, app, client, caplog):
        import logging as stdlib_logging

        @app.route("/trigger-500-log")
        def _h():
            raise RuntimeError("boom-with-trace")

        with caplog.at_level(stdlib_logging.ERROR, logger=app.logger.name):
            resp = client.get("/trigger-500-log")
            assert resp.status_code == 500

        matching = [r for r in caplog.records
                    if "Unhandled exception" in r.getMessage()]
        assert matching, (
            f"Expected 'Unhandled exception' log record, got: "
            f"{[r.getMessage() for r in caplog.records]}"
        )
        # exc_info=True should populate exc_info on the log record
        assert any(r.exc_info is not None for r in matching)

    def test_handler_does_not_swallow_exception_status(self, app, client):
        @app.route("/trigger-value-error")
        def _h():
            raise ValueError("xyz")

        resp = client.get("/trigger-value-error")
        assert resp.status_code == 500
        assert resp.get_json()["status"] == 500
