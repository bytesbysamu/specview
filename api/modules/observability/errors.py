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

from flask import jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException


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
