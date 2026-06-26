"""JSON error handlers for the Flask app.

Provides a single ``register_error_handlers(app)`` consumed by
``create_app()``. The error envelope matches the existing inline handlers in
``create_app.py`` so the wrap-up commit that lifts them out can swap in this
module without an Angular interceptor or test breakage:

    HTTPException     -> {"error": <description>, "status": <code>}, <code>
    ValidationError   -> {"error": "validation_failed",
                          "details": [...],
                          "status": 422}, 422
    Exception (catch) -> {"error": "Internal server error",
                          "status": 500}, 500   (with app.logger.error stack)
"""

import uuid

from flask import g, has_request_context, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException


def request_id() -> str:
    """Return a stable per-request id.

    Uses ``g.request_id`` when set by the app's ``before_request`` hook so the
    value in the error body matches the ``X-Request-ID`` response header. Falls
    back to a fresh uuid4 when called outside that hook (e.g. blueprint-only
    unit tests that register a bare Flask app without the central before_request).
    """
    if has_request_context():
        rid = getattr(g, "request_id", None)
        if rid:
            return rid
        rid = str(uuid.uuid4())
        g.request_id = rid
        return rid
    return str(uuid.uuid4())


def error_envelope(code: str, message: str) -> dict:
    """The single Core error envelope: ``{code, message, request_id}``.

    ``error`` is retained as a deprecated alias of ``message`` for backward
    compatibility with the existing Angular interceptor and pre-existing tests;
    it can be dropped once every consumer reads ``message``.
    """
    return {
        "code": code,
        "message": message,
        "request_id": request_id(),
        "error": message,
    }


def core_error(code: str, message: str, status: int):
    """Build a ``(response, status)`` tuple carrying the unified envelope.

    Routes return this directly so the envelope is consistent without
    depending on app-level error-handler registration (which blueprint-only
    unit tests skip).
    """
    return jsonify(error_envelope(code, message)), status


def register_error_handlers(app) -> None:
    """Register JSON error handlers on ``app``.

    Call after ``init_logging(app)`` (so the structured logger is configured
    when ``handle_unhandled`` records a stack trace) and before blueprint
    registration (so blueprint-level handlers can override per-route).
    """

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return jsonify({
            "error": "validation_failed",
            "details": exc.errors(),
            "status": 422,
        }), 422

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        return jsonify({
            "error": exc.description,
            "status": exc.code,
        }), exc.code

    @app.errorhandler(Exception)
    def handle_unhandled_exception(exc: Exception):
        app.logger.error("Unhandled exception", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "status": 500,
        }), 500
